# 436.9 판 5 정오 6 6-6 / 정오 7 7-4 커버리지 표 (시험 커밋 `aa810ef1`, 브랜치 `ed5-fix3`)

- 칸: 도구 × 판정 항목 × {정상(종료 0), 부정(종료 1), 판정 불가·결함(종료 2), 기록 불변}.
- 칸마다 그 경우를 단언하는 시험을 `별칭::시험 이름`으로 적는다. 칸이 그 도구 설계상 생길 수 없으면 "해당 없음"과 이유를 적는다(빈 칸 아님).
- 별칭
  - E6 = `05_tests/unit/test_jp3_ed5_erratum6.py`
  - E7 = `05_tests/unit/test_jp3_ed5_erratum7.py`
  - S1 = `05_tests/unit/test_jp3_ed5_s1_stored.py`
  - E1 = `test_jp3_ed5_erratum1.py`
  - PF = `test_jp3_ed5_prelaunch_fix.py`
  - A2 = `test_jp3_addendum_4a2.py`
  - A3 = `test_jp3_addendum_4a3.py`
  - A5 = `test_jp3_addendum_4a5.py`
  - PA2 = `test_jp3_prelaunch_audit2.py`
  - HU = `test_jp3_harness_units.py`
  - ME = `test_jp3_judge_main_e2e.py`
  - J9 = `test_jp3_j9main.py`
  - B12 = `test_jp3_12b_tools.py`
  - CK = `test_jp3_ckdrop.py`
  - P51 = `test_jp3_p51_compare.py`
- 6-6 이행 기록(입력 꼴, 정오 6 112행; 병합 전 감사 S-1)
  - 저장 줄을 복사해 설정 이름·태그·③ 정체성만 판 5 꼴로 바꾸고 `main`으로 끝까지 도는 시험
    - `jp3_baseline_compare`: E6 전부 - 저장 기준선 221456d 줄·T4h(VBG5→VBG6, rev 5→6 봉인 정체성).
    - 저장 파일과 짝을 맞추는 다른 경로: S1 - t8(저장 h10·`main.jsonl` 대 78fd5d2d `j9_t8` 줄), t12(저장 H-6과 그 VBH 복사, 78fd5d2d VBJ0 줄과 그 VBJ 복사), records(고정 T4h SUMS 426·135 이름, 저장 H-6 키, 78fd5d2d 사례 E 줄), case-f(78fd5d2d F 행, 저장 grid), x11(기준선 LSJ4 줄, 78fd5d2d X11 줄), P5-1(78fd5d2d cases·cd 줄 대 판 5 꼴 복사본).
    - 바꾼 것: VBG5→VBG6, ③ rev 5→6(봉인 정체성, `run_extend_start_revision` 6), 태그 `_P3H`→`_P3W`. 저장 줄이 그보다 오래되어 없는 판 5 기록 키는 더했다: P4 증거, 씨앗 기록, 잠금 창 기록, r79 meta `keys_file`, 등급(L2 normal·L3 conservative, 판 4a r79 출력 꼴).
    - t12 판정 파일은 모든 줄을 이름으로 적은 합성 파일이고 등급은 pass로 바꿔 둔다(`j9_runs/**/judge`는 읽지 않음).
  - 저장 기록에 그 판 5 키가 없어 손으로 만든 꼴을 유지하는 도구(감사 S-1이 받아들임): 12b(VBK·VBK0의 `rod_fault` 기록), ckdrop, P5-2·P5-4 기록.
  - 그 밖의 칸(판정 항목별 부정·판정 불가 사례)은 각 파일의 합성 도우미 입력이다(판 4a·판 5 시험, 판 5 출력 꼴).
  - 판 4a(78fd5d2d) 출력은 입력으로 썼다(판 5 판정 값을 보는 일이 아님, 감사 S-1). 판 5(ae9d0b2d) 출력은 어떤 시험에도 쓰지 않았다.
- 실행: 이 표의 시험 파일은 모두 `fix3_all_aa810ef1.txt` 묶음에 들어 있다.

## jp3_baseline_compare (단계 4a, 정오 6 6-1·6-2·6-2A, 정오 7 7-1·7-2)

| 판정 항목 | 정상 | 부정(종료 1) | 판정 불가·결함(종료 2) | 기록 불변 |
|---|---|---|---|---|
| 짝짓기(6-1, VBG6→VBG5) | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes, E6::test_pairing_map_is_the_p51_constant | 해당 없음: 짝짓기는 판정이 아니라 입력 조건이다(짝이 없으면 판정 불가) | E6::test_baseline_row_without_a_new_row_is_not_judgeable | 해당 없음: 기록 항목 없음 |
| P4-1 명령 해시(모든 줄) | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | E6::test_each_judged_item_fails_alone (E P4-1, A P4-1, C P4-1) | 해당 없음: 해시 없음은 판정 불가가 아니라 도구 오류(종료 3)다(`_compare_pair`가 읽고 `main`이 모든 예외를 `error`로 낸다), E6::test_p4_1_without_a_command_hash_is_a_tool_error | 해당 없음: 기록 항목 없음 |
| 정체성 13.6(rev 6) | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | 해당 없음: 정체성 불일치는 설정 결함(종료 2)이다 | E6::test_rev6_identity_defect_is_a_setting_defect | 해당 없음: 기록 항목 없음 |
| P4 증거 B2(A·C 포함) | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | 해당 없음: 증거 불일치는 설정 결함(종료 2)이다 | E6::test_a_and_c_p4_evidence_is_judged | 해당 없음: 기록 항목 없음 |
| 판정 행·분류 읽기(13.1) | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | 해당 없음: 판정 행 0은 실패가 아니라 판정 불가다 | ME::test_baseline_compare_finds_each_new_t4h_next_to_its_rows_file | 해당 없음: 기록 항목 없음 |
| P4-2 rev 4·5 줄(판정) | A2::test_p4_2_chain_after_a_retraction_stretch_is_explained | A2::test_p4_2_raise_after_the_chain_broke_is_unexplained | A2::test_p4_2_revision_5_pair_without_its_trace_is_not_judgeable | E6::test_rev4_unchanged_and_rev6_p4_records (rev 4 짝은 judged 표시 유지) |
| P4-2·P4-4·P4-9 rev 6 줄(기록, 6-2) | E6::test_rev4_unchanged_and_rev6_p4_records | 해당 없음: 기록 항목이다(6-2) | 해당 없음: 계산 안 됨은 기록이다(7-2), E6::test_rev6_p4_2_not_computed_is_no_pass | E6::test_rev6_p4_records_do_not_change_the_status |
| P4-3a 판정 키(E) | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | E6::test_each_judged_item_fails_alone (E P4-3a) | A2::test_missing_p4_3a_key_is_not_judgeable | 해당 없음: 기록 항목 없음 |
| P4-4 씨앗 rev 5(판정, 4a) | A2::test_p4_4_seed_net_force_rules | A2::test_p4_4_seed_net_force_rules | A2::test_p4_4_seed_net_force_rules | E6::test_rev6_p4_records_do_not_change_the_status (rev 6 P4-4는 기록) |
| 6-2A B J-P3a | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | E6::test_each_judged_item_fails_alone (B J-P3a) | E6::test_case_bd_rows_missing_is_not_judgeable | 해당 없음: J-P3a는 다섯 줄 모두 판정 |
| 6-2A B J-P3b | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | E6::test_each_judged_item_fails_alone (B J-P3b) | E6::test_case_bd_rows_missing_is_not_judgeable | E6::test_case_b_lsh3_jp3b_and_jp3c_are_records (LSH3 J-P3b, J-P3c) |
| 6-2A (D-가) | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | E6::test_each_judged_item_fails_alone (D-가) | E6::test_case_bd_rows_missing_is_not_judgeable | 해당 없음: 기록 항목 없음 |
| 6-2A (D-나) 덮음 | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | E6::test_covering_fails_when_the_vbg6_gap_is_not_positive | E6::test_not_judgeable_breach_records (C 위반 0, 건수 2, 첫 시각 없음), E6::test_not_judgeable_without_a_vbg6_read_at_the_breach_time | E6::test_covering_records_of_c_do_not_change_the_status |
| 6-2A (D-다) 수치 조건 | E6::test_numeric_conditions_judged_under_the_same_order | E6::test_numeric_conditions_fail_under_the_same_order, E6::test_case_bd_d_carry_ret_fails_numeric_when_same_order | E6::test_u_hold_and_the_vbg6_hold_speed_record (hold_speed 결함) | E6::test_numeric_conditions_are_records_in_another_order, E6::test_case_bd_d_numeric_requires_extension_at_49_1, E6::test_case_bd_d_numeric_unjudgeable_is_record (계산 안 됨 세 경우) |
| 상태 순서(정오 2 2-10) | E6::test_vbg6_pairs_with_the_baseline_vbg5_row_and_the_set_passes | E6::test_a_failure_outranks_a_not_judgeable_reason | E6::test_not_judgeable_breach_records | E6::test_a_failure_outranks_a_not_judgeable_reason (다른 분류 사유 유지) |

## jp3_case_judge (x11·case-f, 단계 4a·4b)

| 판정 항목 | 정상 | 부정(종료 1) | 판정 불가·결함(종료 2) | 기록 불변 |
|---|---|---|---|---|
| x11 P4-5a | E7::test_x11_main_pass_failure_and_not_judgeable, ME::test_x11_main, S1::test_x11_on_the_baseline_lsj4_and_the_stored_x11_row | E7::test_x11_main_pass_failure_and_not_judgeable | E7::test_x11_main_pass_failure_and_not_judgeable | 해당 없음: 판 5 단계 (4a)는 기록 인자 `--fresh-only`를 넘기지 않는다 |
| case-f F-A·F-B·F-E | A2::test_r7_case_f_judge_statuses, ME::test_case_f_mains, S1::test_case_f_on_the_stored_rows_in_the_edition5_form | A2::test_r7_case_f_judge_statuses, E7::test_case_f_records_do_not_change_the_status | A2::test_r7_case_f_judge_statuses | E7::test_case_f_records_do_not_change_the_status |
| case-f-path(F-A 경로) | A3::test_k8_path_equivalence_statuses, ME::test_case_f_mains | A3::test_k8_path_equivalence_statuses | A3::test_k8_path_equivalence_statuses, A3::test_k8_grid_sha_is_asserted | 해당 없음: 기록 항목 없음 |

## jp3_tjr_judge (t8·t12·records)

| 판정 항목 | 정상 | 부정(종료 1) | 판정 불가·결함(종료 2) | 기록 불변 |
|---|---|---|---|---|
| t8 T-JR-10 | ME::test_t8_main, A3::test_k1_allowed_differences_pass_and_the_c_record_is_written, S1::test_t8_on_the_stored_h10_lines | A3::test_k1_t8_conditions | A3::test_k1_t8_needs_exactly_the_22_jobs, A5::test_e2_stored_hash_not_64_characters_is_not_judgeable | A3::test_k1_c_record_compares_the_fallback_estimates, PA2::test_n4_vb_lines_without_p4_readings_pass |
| t8 T-JR-11 | ME::test_t8_main, S1::test_t8_on_the_stored_h10_lines | A5::test_e2_64_character_hashes_that_differ_still_fail, S1::test_t8_on_the_stored_h10_lines | A5::test_e2_hash_not_64_characters_is_not_judgeable | PA2::test_n4_vb_line_with_p4_readings_makes_t_jr_10_not_judgeable (T-JR-11은 pass 유지) |
| t12 VBH·VBJ(T-JR-12a) | A2::test_b4_t12_counts_faults_and_ready, ME::test_t12_main, S1::test_t12_vbh_on_the_stored_h6, S1::test_t12_vbj_on_the_stored_vbj0_lines | A2::test_b4_t12_counts_faults_and_ready, E1::test_t12_vbj_report_carries_the_jp3_outcome | PA2::test_n1_t12_command_lock_window_mismatch_exit_2, A5::test_e4_t12_vbj_j_p3_judged_key_missing_is_not_judgeable | PA2::test_t12_record_failures_are_the_13_9_list, E1::test_record_gate_13_9_record_failure_alone_goes_on |
| records T-JR-13 | E7::test_records_main_passes_on_the_valid_set, A5::test_e1_records_command_exit_codes, S1::test_records_on_the_stored_t4h_lists_and_h6_keys | A5::test_e1_records_command_exit_codes, A5::test_e1_replay_error_row_fails | A5::test_e1_records_command_exit_codes, A5::test_e1_replay_reports_not_judgeable, E1::test_t_jr_13_takes_revision_6_reports_only | E7::test_records_t_jr_13_replay_jp3_and_runs_over_are_records |
| records T-JR-14 | E7::test_records_main_passes_on_the_valid_set, S1::test_records_on_the_stored_t4h_lists_and_h6_keys | PA2::test_n1_records_command_exit_1, A5::test_e1b_late_fallback_fails | A5::test_e1b_not_judgeable | E7::test_records_t_jr_14_leg_records_do_not_change_the_status |
| records T-JR-15 | E7::test_records_main_passes_on_the_valid_set, HU::test_t_jr_15_retract_seed_rows_and_net_force, S1::test_records_on_the_stored_t4h_lists_and_h6_keys | E7::test_records_t_jr_15_vbj_relock_fails_through_main, A5::test_e1c_relock_and_seed | E7::test_records_t_jr_15_missing_relock_is_not_judgeable_through_main, A5::test_e1c_judged_set_is_fixed, A2::test_b4_records_seed_force_rules | E7::test_records_t_jr_15_vbh_rows_are_records |

## jp3_12b_judge (단계 6b·6c)

| 판정 항목 | 정상 | 부정(종료 1) | 판정 불가·결함(종료 2) | 기록 불변 |
|---|---|---|---|---|
| decide(A/A·N·k 보충) | B12::test_12b_pass_end_to_end, B12::test_12b_needs_b4_and_b4_counts_its_opportunity_pairs | 해당 없음: decide는 결정 기록이고 종료 1이 없다(0 decided·needs, 2 멈춤; 원판 6.3.8) | B12::test_12b_aa_floor_stop_and_no_vbk_file_read, B12::test_12b_needs_b3_then_b3_below_301_is_not_judgeable, B12::test_12b_vbk0_not_latched_stops_the_decision | B12::test_12b_aa_two_pairs_and_rounding_do_not_stop |
| judge 12b (1)~(4) | B12::test_12b_pass_end_to_end | B12::test_12b_new_fault_after_a_truncated_row_event_list_fails, B12::test_12b_ready_rules, B12::test_12b_jp3_breach_fails_and_missing_inputs_are_not_judgeable, B12::test_12b_failure_and_setting_defect_is_exit_1_with_both | B12::test_12b_decision_sha_and_status_are_checked, B12::test_12b_no_failure_and_not_judgeable_is_exit_2, B12::test_12b_stop_before_judging_is_exit_2_even_with_a_failing_pair, B12::test_12b_setting_defects | B12::test_12b_new_fault_judged_on_ready_missing_pairs_recorded_on_fallback, B12::test_w6_grade_transitions_are_computed, B12::test_f1_pass_without_both_grade_files_is_exit_0 |
| grade-judge | B12::test_w6_grade_judge_runs_the_r79_judge_and_records_the_sha | 해당 없음: 기록 도구라 종료 1이 없다(0·2·3, 정오 2 2-1) | B12::test_w6_grade_judge_runs_the_r79_judge_and_records_the_sha | B12::test_f1_failure_with_a_grade_input_defect_is_exit_1 (등급 입력 결함이 판정 상태를 바꾸지 않음) |

## jp3_j9main_judge (단계 8)

| 판정 항목 | 정상 | 부정(종료 1) | 판정 불가·결함(종료 2) | 기록 불변 |
|---|---|---|---|---|
| J 항목(VBJ J1~J11, R15, S8) | J9::test_synthetic_rev6_only_passes | J9::test_synthetic_failure_with_no_reference_is_exit_1, J9::test_status_order, J9::test_s8_f5_record_sa4_failure_and_stop | J9::test_synthetic_r15_not_judgeable_alone_is_exit_2, J9::test_s8_stop_value_none_is_not_judgeable | J9::test_baseline_failures_of_every_pair, J9::test_s8_f5_record_sa4_failure_and_stop |
| LS 조건(L-a~L-e) | J9::test_synthetic_rev6_only_passes | J9::test_status_order, E7::test_j9main_l_d_is_a_record_and_l_b_l_e_fail | J9::test_limit_cycle_and_r15_rules | E7::test_j9main_l_d_is_a_record_and_l_b_l_e_fail |
| J-P3 rev 6·정체성 H-2 | J9::test_synthetic_rev6_only_passes | J9::test_status_basis_reads_jp3_h7_and_keeps_the_defect, J9::test_synthetic_jp3_without_rows_and_a_failure_is_exit_1 | J9::test_synthetic_identity_defect_is_a_setting_defect, J9::test_judge_end_to_end_on_stored_lines | J9::test_status_basis_reads_jp3_h7_and_keeps_the_defect (결함 사유 유지) |
| V0 표본(2-7.1) | J9::test_v0_sample_same_differs_and_refusals | J9::test_v0_sample_same_differs_and_refusals | J9::test_v0_sample_same_differs_and_refusals | 해당 없음: 기록 항목 없음 |

## ckdrop 기록 (`jp3_ckdrop_record.py`, 단계 7b, 기록 묶음)

| 판정 항목 | 정상 | 부정(종료 1) | 판정 불가·결함(종료 2) | 기록 불변 |
|---|---|---|---|---|
| T-CK·DROPOUT 기록 | CK::test_record_lines_and_not_computed, CK::test_tck_pairs_new_faults_and_ready | 해당 없음: 기록 도구라 종료 1이 없다(0 written, 2 입력, 3 오류; 정오 2 2-9.5) | CK::test_record_lines_and_not_computed (잘못된 인자 종료 2) | CK::test_tck_pairs_missing_t4h_is_not_computed, CK::test_record_lines_and_not_computed (계산 안 됨) |

## P5-1·P5-2·P5-4

| 판정 항목 | 정상 | 부정(종료 1) | 판정 불가·결함(종료 2) | 기록 불변 |
|---|---|---|---|---|
| P5-1 명령 해시 대 78fd5d2d | P51::test_p51_equal_rows_pass_and_fallback_rows_are_recorded, E1::test_p51_x11_always_equal_and_vbg6_pairs_with_vbg5, S1::test_p51_on_the_stored_rows_and_their_edition5_copies | P51::test_p51_a_differing_judged_pair_stops, E1::test_p51_differ_outranks_the_problems, S1::test_p51_changed_hash_of_an_always_judged_row_stops | P51::test_p51_not_judgeable_cases, P51::test_p51_reads_the_t4h_event_list | P51::test_p51_equal_rows_pass_and_fallback_rows_are_recorded (대체 짝은 기록) |
| P5-2 대조(p52-compare) | PF::test_p52_compare_pass_differ_judged_and_not_judgeable | PF::test_p52_compare_pass_differ_judged_and_not_judgeable | PF::test_p52_compare_without_a_fixed_count_is_not_judgeable, PF::test_p52_compare_pass_differ_judged_and_not_judgeable | PF::test_p52_judged_total_counts_the_p4_on_rev6_rows_only |
| P5-4 기록(p54) | PF::test_p54_record_lists_the_input_files_sha, E7::test_p54_main_written_not_usable_and_record | 해당 없음: 기록 도구라 종료 1이 없다(P5-4는 기록) | E7::test_p54_main_written_not_usable_and_record | E7::test_p54_main_written_not_usable_and_record (감소율과 무관하게 종료 0) |
