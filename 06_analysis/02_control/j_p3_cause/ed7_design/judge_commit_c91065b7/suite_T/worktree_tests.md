# worktree_tests — worktree 코드 + 메인 checkout 저장 자료 시험

- worktree `C:\workspace\outrigger_control\.claude\worktrees\ed7-judge`, 데이터 root `C:\workspace\outrigger_control`, 바꾼 폴더 07_results
- pytest 종료 0(모든 시험 통과), 3334.2 s · 시험 2650: 통과 2650, 실패 0, 오류 0, 건너뜀 0, 예상 실패 0, XPASS 0
- probe: `outrigger_sim` worktree, `jp3_ed7_judge` worktree
- 실행 중 바뀐 데이터 경로 0회, 원본 불변 True, 실행 폴더 삭제 False
- 오류 0 · 경고 8 · 참고 86

## 복사본

| 파일 | 시험 | `__file__` | 감싼 경로 | 감싸지 않은 글자 |
|---|---|---|---|---|
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
| `05_tests/unit/test_ed6_erratum2.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_erratum3.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_harness.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed6_judges.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed6_lock_start_b.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_prelock.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed6_tjr_12a.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed7_adoption.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed7_harness.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed7_judge.py` | 예 | 2 | - | 0 |
| `05_tests/unit/test_ed7_run_commit.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_ed7_units.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_extend_start_bound.py` | 예 | 0 | - | 0 |
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
| `05_tests/unit/test_resume4368_rev10.py` | 예 | 1 | - | 4 |
| `05_tests/unit/test_resume4368_rev11.py` | 예 | 1 | - | 1 |
| `05_tests/unit/test_resume4368_rev12.py` | 예 | 1 | 219: `tmp_path / "07_results"` | 0 |
| `05_tests/unit/test_resume4368_rev16.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_resume4368_rev7.py` | 예 | 1 | - | 0 |
| `05_tests/unit/test_resume4368_rev8.py` | 예 | 1 | - | 1 |
| `05_tests/unit/test_resume4368_rev9.py` | 예 | 1 | - | 0 |
| `05_tests/conftest.py` | - | 1 | - | 0 |

## 발견 사항

### 경고 (warning) — 8건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| data_literal_not_rebased | 05_tests/unit/test_c2_retrigger_two_samples.py:59 |  | 감싸지 않은 데이터 경로 글자 'C:\\workspace\\outrigger_control\\07_results\\S8': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev10.py:66 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/batch_': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev10.py:79 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/some_folder': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev10.py:80 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/batch_V5-RESUME-K1-ZZ_20261113_120000': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev10.py:81 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/some_folder': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev11.py:479 |  | 감싸지 않은 데이터 경로 글자 'C:\\workspace\\outrigger_control\\07_results\\S9': 여기는 worktree를 읽는다 |
| data_literal_not_rebased | 05_tests/unit/test_resume4368_rev8.py:459 |  | 감싸지 않은 데이터 경로 글자 '07_results/S9/batch_': 여기는 worktree를 읽는다 |
| rebase_never_used | probe |  | 실행 중 데이터 경로가 한 번도 바뀌지 않았다 |

### 참고 (info) — 86건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
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
| no_data_paths | 05_tests/unit/test_ed6_erratum2.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_erratum3.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_harness.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_judges.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_lock_start_b.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_prelock.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed6_tjr_12a.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_adoption.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_harness.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_judge.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_run_commit.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_ed7_units.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_extend_start_bound.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
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
| no_data_paths | 05_tests/unit/test_resume4368_rev10.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev11.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev16.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev7.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev8.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| no_data_paths | 05_tests/unit/test_resume4368_rev9.py |  | 바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다) |
| probe_worktree | probe | outrigger_sim | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed7-judge\03_src\outrigger_sim\__init__.py (main) |
| probe_worktree | probe | jp3_ed7_judge | worktree에서 import됨: C:\workspace\outrigger_control\.claude\worktrees\ed7-judge\04_scripts\04_hydraulic\coupled\jp3_ed7_judge.py (main) |
| rebase_unmatched | probe |  | worktree·데이터 root 밖이라 그대로 둔 값 1회: ['C:\\Users\\jinbeom\\AppData\\Local\\Temp\\pytest-of-jinbeom\\pytest-3385\\test_judge_row_without_window_0\\07_results'] |


## pytest 로그 끝

```text
........................................................................ [  2%]
........................................................................ [  5%]
........................................................................ [  8%]
........................................................................ [ 10%]
........................................................................ [ 13%]
........................................................................ [ 16%]
........................................................................ [ 19%]
........................................................................ [ 21%]
........................................................................ [ 24%]
........................................................................ [ 27%]
........................................................................ [ 29%]
........................................................................ [ 32%]
........................................................................ [ 35%]
........................................................................ [ 38%]
........................................................................ [ 40%]
........................................................................ [ 43%]
........................................................................ [ 46%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 54%]
........................................................................ [ 57%]
........................................................................ [ 59%]
........................................................................ [ 62%]
........................................................................ [ 65%]
........................................................................ [ 67%]
........................................................................ [ 70%]
........................................................................ [ 73%]
........................................................................ [ 76%]
........................................................................ [ 78%]
........................................................................ [ 81%]
........................................................................ [ 84%]
........................................................................ [ 86%]
........................................................................ [ 89%]
........................................................................ [ 92%]
........................................................................ [ 95%]
........................................................................ [ 97%]
..........................................................               [100%]
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

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2650 passed, 7 warnings in 3332.40s (0:55:32)
```
