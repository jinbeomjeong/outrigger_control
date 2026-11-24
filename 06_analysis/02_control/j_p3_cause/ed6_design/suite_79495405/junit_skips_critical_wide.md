# 시험 건너뜀 점검 (junit_skips)

- 보고서 1개, 시험 8587개: 통과 8570, 실패 2, 오류 0, 건너뜀 15, 예상 실패 0, 예상 실패 통과 0(필수 0)
- 건너뜀·예상 실패는 통과가 아니다. 필수 시험의 건너뜀·예상 실패는 미실행으로 센다.
- JUnit XML에는 xfail의 strict 여부가 없고, strict 아닌 XPASS는 통과로 적힌다.

## 건너뜀

| 시험 | 결과 | 종류 | strict | 사유 |
|---|---|---|---|---|
| `05_tests.unit.test_d8x_chrono_rows::test_refuses_without_verification_ext` | skipped | pytest.skip | - | VERIFICATION_EXT installed |
| `05_tests.unit.test_las_chrono_rows::test_run_refuses_blocked_rows` | skipped | pytest.skip | - | LAS-b merged: no blocked row |
| `05_tests.unit.test_ml_pipeline::test_gru_onnx_dynamo_export_matches_torch` | skipped | pytest.skip | - | could not import 'torch': No module named 'torch' |
| `05_tests.unit.test_ml_pipeline::test_gru_onnx_falls_back_to_torchscript` | skipped | pytest.skip | - | could not import 'torch': No module named 'torch' |
| `05_tests.unit.test_ml_pipeline::test_float32_thresholds_keep_every_booster_decision` | skipped | pytest.skip | - | could not import 'torch': No module named 'torch' |
| `05_tests.unit.test_ml_pipeline::test_lightgbm_onnx_export_matches_booster` | skipped | pytest.skip | - | could not import 'torch': No module named 'torch' |
| `05_tests.unit.test_ml_pipeline::test_training_export_and_scoring_run_end_to_end` | skipped | pytest.skip | - | could not import 'torch': No module named 'torch' |
| `05_tests.unit.test_params_l2b::test_l1_default_is_unchanged` | skipped | pytest.skip | - | YAML regenerated since S7; L1 fingerprint baseline no longer applies |
| `05_tests.unit.test_rod_chamber::test_h6_gas_separation` | skipped | pytest.skip | - | gas separation after FLOOR (14.3 optional) is not implemented |
| `05_tests.unit.test_s8_soil_restore::test_soil_restore_check_reads_the_plan_of_this_tree` | skipped | pytest.skip | - | S8 ML plan not present (07_results is not tracked): C:\workspace\outrigger_control\.claude\worktrees\ed6-run6\07_results\S8\ml_main_20261025_090131\ml_plan.json |
| `05_tests.unit.test_s9_final::test_source_args_check_on_the_former_runs` | skipped | pytest.skip | - | no former run folders under 07_results/S9 |
| `05_tests.unit.test_s9_final::test_final_r_s6_rows_match_their_former_batch` | skipped | pytest.skip | - | former S6 batch not here |
| `05_tests.unit.test_s9_final::test_final_rep_x_check_sources` | skipped | pytest.skip | - | source run folder absent (07_results is not in git) |
| `05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ5-VBJ]` | skipped | pytest.skip | - | X10_BASE_ROOT not set (a checkout of the commit before X-10) |
| `05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ0-VBJ0]` | skipped | pytest.skip | - | X10_BASE_ROOT not set (a checkout of the commit before X-10) |

## 예상 실패 (xfail·XPASS)

예상 실패 없음.

## 발견 사항

### 오류 (error) — 2건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| test_failed | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_d8x_diag::test_rerun_gives_the_stored_command_hash | 05_tests.unit.test_d8x_diag::test_rerun_gives_the_stored_command_hash: failed (AssertionError: assert 'c0b626b9d8ed...4ad4093a8c758' == '4700d690fb09...c802b1e591729' - 4700d690fb098a3760f40dde032feb49461c081aa97453156d5c802b1e591729 + c0b626b9d8ed1fabcc647701e802a567fcae0b69784) |
| test_failed | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_record::test_default_snapshot_directory_is_results_states | 05_tests.unit.test_record::test_default_snapshot_directory_is_results_states: failed (AssertionError: assert WindowsPath('C:/workspace/outrigger_control/.claude/worktrees/ed6-run6/07_results/states') == (WindowsPath('C:/workspace/outrigger_control/07_results') / 'states') + where Windo) |

### 참고 (info) — 15건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_d8x_chrono_rows::test_refuses_without_verification_ext | 05_tests.unit.test_d8x_chrono_rows::test_refuses_without_verification_ext: 건너뜀 (pytest.skip: VERIFICATION_EXT installed) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_las_chrono_rows::test_run_refuses_blocked_rows | 05_tests.unit.test_las_chrono_rows::test_run_refuses_blocked_rows: 건너뜀 (pytest.skip: LAS-b merged: no blocked row) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_ml_pipeline::test_gru_onnx_dynamo_export_matches_torch | 05_tests.unit.test_ml_pipeline::test_gru_onnx_dynamo_export_matches_torch: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_ml_pipeline::test_gru_onnx_falls_back_to_torchscript | 05_tests.unit.test_ml_pipeline::test_gru_onnx_falls_back_to_torchscript: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_ml_pipeline::test_float32_thresholds_keep_every_booster_decision | 05_tests.unit.test_ml_pipeline::test_float32_thresholds_keep_every_booster_decision: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_ml_pipeline::test_lightgbm_onnx_export_matches_booster | 05_tests.unit.test_ml_pipeline::test_lightgbm_onnx_export_matches_booster: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_ml_pipeline::test_training_export_and_scoring_run_end_to_end | 05_tests.unit.test_ml_pipeline::test_training_export_and_scoring_run_end_to_end: 건너뜀 (pytest.skip: could not import 'torch': No module named 'torch') |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_params_l2b::test_l1_default_is_unchanged | 05_tests.unit.test_params_l2b::test_l1_default_is_unchanged: 건너뜀 (pytest.skip: YAML regenerated since S7; L1 fingerprint baseline no longer applies) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_rod_chamber::test_h6_gas_separation | 05_tests.unit.test_rod_chamber::test_h6_gas_separation: 건너뜀 (pytest.skip: gas separation after FLOOR (14.3 optional) is not implemented) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_s8_soil_restore::test_soil_restore_check_reads_the_plan_of_this_tree | 05_tests.unit.test_s8_soil_restore::test_soil_restore_check_reads_the_plan_of_this_tree: 건너뜀 (pytest.skip: S8 ML plan not present (07_results is not tracked): C:\workspace\outrigger_control\.claude\worktrees\ed6-run6\07_results\S8\ml_main_20261025_090131\ml_plan.json) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_s9_final::test_source_args_check_on_the_former_runs | 05_tests.unit.test_s9_final::test_source_args_check_on_the_former_runs: 건너뜀 (pytest.skip: no former run folders under 07_results/S9) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_s9_final::test_final_r_s6_rows_match_their_former_batch | 05_tests.unit.test_s9_final::test_final_r_s6_rows_match_their_former_batch: 건너뜀 (pytest.skip: former S6 batch not here) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_s9_final::test_final_rep_x_check_sources | 05_tests.unit.test_s9_final::test_final_rep_x_check_sources: 건너뜀 (pytest.skip: source run folder absent (07_results is not in git)) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ5-VBJ] | 05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ5-VBJ]: 건너뜀 (pytest.skip: X10_BASE_ROOT not set (a checkout of the commit before X-10)) |
| skipped | C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\suite_79495405\junit_run_79495405.xml | 05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ0-VBJ0] | 05_tests.unit.test_x10_rod_fault::test_i_without_a_plan_the_rows_are_the_commit_before_x10[VBJ0-VBJ0]: 건너뜀 (pytest.skip: X10_BASE_ROOT not set (a checkout of the commit before X-10)) |
