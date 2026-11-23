# 436.9 판 5 정오 8 8-8.3 / 정오 7 7-4 커버리지 표 (시험 커밋 `d4162add`, 브랜치 `ed5-tool8`)

- 커밋: 판정 도구·실행 스크립트 `c895bb72`(c895bb7285e16bf70796651cfe14063bf7737ff4), 시험 보강 `d4162add`(d4162addfbfb9d4af90784922b68c9e3b6c5f8af, `05_tests/unit/test_jp3_12b_erratum8.py`만 바뀜). 이 표와 junit 기록은 그 뒤 커밋으로 더한다(`06_analysis/` 추가만).

- 대상: 정오 8(`jp3_remedy_spec_v5_erratum8.md`, 봉인 cd2de978) 8-8 `jp3_12b_judge.py`(decide·judge)와 8-9 실행 스크립트의 파일만 읽는 관문(`run_steps_ed5/e8_gates_ed5.ps1`).
- 칸: 도구 × 판정 항목 × {정상(종료 0), 부정(종료 1), 판정 불가·결함(종료 2), 기록 불변}. 칸마다 그 경우를 단언하는 시험을 `별칭::시험 이름`으로 적는다. 칸이 설계상 생길 수 없으면 "해당 없음"과 이유를 적는다(빈 칸 아님).
- 별칭
  - E8 = `05_tests/unit/test_jp3_12b_erratum8.py`(정오 8 8-8.3 시험 1~14는 `test_e8_01`~`test_e8_14`, 실행 스크립트 관문은 `test_e8_gate_*`)
  - B12 = `05_tests/unit/test_jp3_12b_tools.py`(정오 8에 맞춰 고친 기존 12b 시험)
- 입력 꼴: 모두 `tmp_path` 아래 합성 출력이다(r79 러너 꼴의 결과 줄 + T4h npz, `test_jp3_12b_tools.py`의 `Arm` 빌더). `j9_runs/`의 파일은 어떤 시험도 읽지 않는다. 8-7 블라인드 파일(c 건식 VBK `VBK_c92*`·`VBK_c93*`, `cdry_a1/logs/`, 12b VBK 출력)은 시험·픽스처에 쓰지 않았다(E8::test_e8_12_no_blind_file_in_tests_or_fixtures가 두 시험 파일의 글자로 확인).
- 실행: `e8set_d4162add.txt`의 6파일, `junit_d4162add_e8set.*`(이 폴더). 인터프리터 dynamics-dev `python.exe -B -m pytest -q -p no:cacheprovider`(지시 2026-11-23), `--cov=04_scripts/04_hydraulic/coupled --cov-branch`, 그 뒤 `junit_skips.py --critical . --fail-on-skip`. worktree는 실행 전후 깨끗했다(record.json `clean_before`·`clean_after`).

## 8-8.3 시험 번호 대응

| 8-8.3 | 시험 |
|---|---|
| 1 | E8::test_e8_01_b1_b2_allowance_7 (n23 = 7 → pass 종료 0, 8 → failed 종료 1) |
| 2 | E8::test_e8_02_b1_b2_b4_allowance_9 (9 → pass, 10 → failed, b4 짝은 TRw 층) |
| 3 | E8::test_e8_03_b3_is_not_judgeable (b3 결정 기록 → 종료 2, b3 요구 decide → 종료 2, `needs_b3`·`aa_floor_stop` 상태 없음, `step6b_vbk0.ps1 -Phase b3`는 아무것도 하지 않고 종료 2), B12::test_12b_b3_needed_or_given_is_not_judgeable |
| 4 | E8::test_e8_04_ready_delay_boundary (130.000001 셈, 130.0·130.0000004 안 셈, 30.0000005 안 씀) |
| 5 | E8::test_e8_05_vbk0_without_ready |
| 6 | E8::test_e8_06_stall_signature (서명 만족 1, 서명 아님 3: 행정 폭 3.6 mm·마지막 단계 done·fault 단계 진입) |
| 7 | E8::test_e8_07_decide_records_aa_and_goes_on, B12::test_12b_aa_three_pairs_are_a_record_and_no_vbk_file_read |
| 8 | E8::test_e8_08_failures_and_their_order[new_fault / h7 / n23_and_defect] |
| 9 | E8::test_e8_09_decision_blocks_and_allowance |
| 10 | E8::test_e8_10_no_opportunity_pair_is_not_judgeable |
| 11 | E8::test_e8_11_record_item_exceptions_keep_the_status |
| 12 | E8::test_e8_12_no_blind_file_in_tests_or_fixtures |
| 13 | E8::test_e8_13_expected_vbk0_inputs |
| 14 | E8::test_e8_14_b4_chain (도구 사슬과 실행 스크립트 관문: 두 번째 `needs_b4`는 종료 2, `12b_decide_e8_b4.done`이 있으면 그 결정 기록), E8::test_e8_14_b4_below_45_is_not_judgeable |

## jp3_12b_judge (단계 12b_decide_e8·12b_decide_e8_b4·12b_vbk 판정)

| 판정 항목 | 정상 | 부정(종료 1) | 판정 불가·결함(종료 2) | 기록 불변 |
|---|---|---|---|---|
| decide: A/A 기록(8-1, 8-8.1) | E8::test_e8_07_decide_records_aa_and_goes_on, B12::test_12b_pass_end_to_end | 해당 없음: decide는 실패를 세지 않는다(종료 0·2·3, 정오 2 2-10을 고친 8-10 문장) | B12::test_12b_existing_out_and_tool_errors(이미 있는 `--out` 종료 2) | E8::test_e8_07_decide_records_aa_and_goes_on(4쌍 ≥ 3이어도 멈추지 않음), B12::test_12b_aa_three_pairs_are_a_record_and_no_vbk_file_read, B12::test_12b_aa_two_pairs_and_rounding |
| decide: 입력 고정(8-9 (d)) | E8::test_e8_13_expected_vbk0_inputs(일치 → decided, `vbk0_expected.matched`) | 해당 없음: 같은 이유 | E8::test_e8_13_expected_vbk0_inputs(결과 sha·T4h 요약 불일치, 인자 없음, b1만, b4 기대값, 형식 틀린 인자, 기대 블록의 VBK0 없음 → 종료 2, 기록은 rule·inputs·status·reason·exit뿐) | 해당 없음: 기록 항목 없음 |
| decide: N 보충·b3(8-8.1) | B12::test_12b_pass_end_to_end | 해당 없음: 같은 이유 | E8::test_e8_03_b3_is_not_judgeable, B12::test_12b_b3_needed_or_given_is_not_judgeable, E8::test_e8_10_no_opportunity_pair_is_not_judgeable(N_opp 0 < 301), B12::test_12b_vbk0_not_latched_stops_the_decision | 해당 없음: 기록 항목 없음 |
| decide: 목격 보충·b4 사슬(6.3.6, 8-9 3) | E8::test_e8_14_b4_chain, B12::test_12b_needs_b4_and_b4_counts_its_opportunity_pairs | 해당 없음: 같은 이유 | E8::test_e8_14_b4_below_45_is_not_judgeable(b4 뒤 k 37 < 45 → 종료 2, 결정 키 없음) | E8::test_e8_14_b4_chain(첫 `needs_b4` 기록에 `blocks_used`·`allow_k` 없음) |
| judge: 결정 기록 검사(8-8.2 W-5, 옛 기록 거부) | B12::test_12b_pass_end_to_end | 해당 없음: 결정 기록 결함은 판정 전 멈춤이라 실패가 없다(종료 2) | E8::test_e8_09_decision_blocks_and_allowance(allow_k 불일치·없음, blocks_used 없음·집합 불일치·반복·목록 아님, allow_k 글자), E8::test_e8_03_b3_is_not_judgeable(b3 결정 기록), B12::test_12b_aa_three_pairs_are_a_record_and_no_vbk_file_read(`aa_floor_stop` 기록), B12::test_12b_decision_sha_and_status_are_checked | 해당 없음: 기록 항목 없음 |
| judge: (2)+(3) n23 ≤ allow_k(8-2) | E8::test_e8_01_b1_b2_allowance_7[4-3-0-pass], E8::test_e8_02_b1_b2_b4_allowance_9[3-0-pass], B12::test_12b_ready_rules, E8::test_e8_04_ready_delay_boundary | E8::test_e8_01_b1_b2_allowance_7[5-3-1-failed], E8::test_e8_02_b1_b2_b4_allowance_9[4-1-failed], E8::test_e8_08_failures_and_their_order[n23_and_defect], B12::test_f1_failure_with_a_grade_input_defect_is_exit_1 | E8::test_e8_10_no_opportunity_pair_is_not_judgeable(기회 짝 0: `verdict` not_judgeable, 실패 없음, 종료 2) | E8::test_e8_05_vbk0_without_ready(VBK0 READY 미도달 짝은 n23 밖, READY 기록) |
| judge: (1) 새 FAULT(분모 N_1) | B12::test_12b_pass_end_to_end(`n_fault_judged` 334), E8::test_e8_05_vbk0_without_ready(N_1 = 기회 332 + VBK0 미도달 2) | E8::test_e8_08_failures_and_their_order[new_fault], B12::test_12b_new_fault_after_a_truncated_row_event_list_fails, B12::test_w5_phase_fault_only_on_vbk_fails_a_ready_missing_pair | B12::test_12b_stop_before_judging_is_exit_2_even_with_a_failing_pair | B12::test_12b_new_fault_judged_on_ready_missing_pairs_recorded_on_fallback |
| judge: (4) J-P3 H-7 | B12::test_12b_pass_end_to_end | E8::test_e8_08_failures_and_their_order[h7], B12::test_12b_jp3_breach_fails_and_missing_inputs_are_not_judgeable, B12::test_12b_jp3_h7_and_setting_defect_is_exit_1 | B12::test_12b_jp3_breach_fails_and_missing_inputs_are_not_judgeable, B12::test_12b_zero_judged_rows_are_not_judgeable | B12::test_judge_jp3_reads_h7_under_a_defect |
| judge: 기록 항목(교착 서명·`n_vbk0_worse*`·`by_cell`·`by_block`, 8-3·8-6·8-8.2 W-4) | E8::test_e8_06_stall_signature, E8::test_e8_04_ready_delay_boundary(`n_vbk0_worse_plus30`), E8::test_e8_05_vbk0_without_ready(`n_vbk0_worse_loss`), E8::test_e8_01·02(`by_block`·`by_cell`·TRw) | 해당 없음: 기록 항목은 판정 상태를 바꾸지 않는다(8-3, 8-8.2) | 해당 없음: 계산 안 됨은 기록이다(8-8.2 W-4); E8::test_e8_06_stall_signature(`t_s` 없음 → computed false) | E8::test_e8_11_record_item_exceptions_keep_the_status(길이 불일치·도우미 예외 → computed false, 상태·종료 코드 같음; 대문자 `LEVEL`), E8::test_e8_06_stall_signature |
| 상태 순서(정오 2 2-10) | B12::test_12b_pass_end_to_end | E8::test_e8_08_failures_and_their_order[n23_and_defect], B12::test_12b_failure_and_setting_defect_is_exit_1_with_both, B12::test_12b_failure_and_not_judgeable_is_exit_1 | B12::test_12b_no_failure_and_not_judgeable_is_exit_2, B12::test_12b_setting_defects | B12::test_f1_failure_with_a_grade_input_defect_is_exit_1(등급 입력 결함이 상태를 바꾸지 않음) |

## 실행 스크립트 관문 (`e8_gates_ed5.ps1`, pwsh에서 따로, `Set-StrictMode -Version 3`)

| 관문 | 계속(go) | 멈춤 2 | 멈춤 3 |
|---|---|---|---|
| 8-9 (a) diff 규칙 `Get-E8DiffStop` | E8::test_e8_gate_diff_rule(허용 9줄, 빈 diff) | 해당 없음: diff 위반은 정체성 위반이라 3이다 | E8::test_e8_gate_diff_rule(D, 06_analysis 기존 파일 M, 공용 `run_steps/`, `pre_las_preset_runner.py`, 러너·`jp3_fixed_inputs.py`·03_src, 다른 시험, R, `.claude/agents/`) |
| 8-9 (a″) 두 고정 목록 `Get-E8FixedListStop` | E8::test_e8_gate_two_fixed_lists | E8::test_e8_gate_two_fixed_lists(옛 목록 미연결, 실행 스크립트 줄이 도구 목록에 없음, 다른 파일 변경) | 해당 없음: 목록 파일 없음만 3(시험 안 함, 아래 공백) |
| 8-9 (c) 실행 조건 `Get-E8EnvironmentStop`·`Get-E8WorkersStop`·`Get-E8IdentityStop` | E8::test_e8_gate_identity_environment_and_workers(마스크·시각·계획·T4h·설정 이름 차이, 선언한 추가 변수) | 같은 시험(스레드 값·head 차이, 선언 안 한 변수, `R79_ROD_MODEL`, 설정 불일치, `--workers` 3) | 해당 없음: 기록 파일 없음·읽기 실패만 3 |
| 8-9 (d)·3 결정 기록 `Get-E8DecisionStop` | E8::test_e8_gate_decision_record_w5, E8::test_e8_14_b4_chain | 같은 두 시험(decided의 allow_k·집합·키 없음, not_judgeable, 두 번째 `needs_b4`) | E8::test_e8_gate_decision_record_w5(파일 없음) |
| 8-9 4 결정 기록 선택 `Get-E8DecisionChoice` | E8::test_e8_14_b4_chain(`12b_decide_e8_b4.done` 우선) | 해당 없음: 선택된 기록의 상태 검사는 위 행 | 해당 없음 |
| 8-9 (e) 멈춘 base 수용 `Get-E8BaseStop` | E8::test_e8_gate_stopped_base_attempt | 같은 시험(done 표지, 멈춤 표지 2개, 종료 1) | 해당 없음 |
| 2-9.6 (8-10) `Get-E8ReadyRuleStop` | E8::test_e8_gate_ready_rule_of_step8(b1 b2 / b1 b2 b4) | 같은 시험(블록 없음, verdict failed·not_judgeable, allow_k 불일치·글자, b3, 키 없음) | 해당 없음 |

## 시험이 닿지 않는 범위(검증 공백)

- `jp3_12b_judge.py`에서 이번에 바꾼 줄 가운데 시험이 닿지 않는 곳(`d4162add` 실행의 커버리지 json과 `git diff -U0 606f8713 c895bb72`의 교집합)
  - `decide`의 `N_opp < 301`(b3 판정 뒤): b3가 필요 없으면 기회 짝이 0.9 × 334 = 300.6 이상, 곧 301 이상이라 닿을 수 없다. 원판 6.3.5의 검사를 지키려고 남긴 방어 줄이다.
  - `is_stall_signature`의 READY 있음 → False: 호출하는 두 곳이 READY 없는 줄만 넘기므로 닿지 않는다(8-3 조건 1의 방어 줄).
  - 그 밖의 바뀐 줄·분기는 모두 실행되었다(`바뀐 375줄 가운데 실행되지 않은 줄은 위 2곳(566행, 827행)뿐이다. 도구 전체: 문장 904, 미실행 57, 분기 340, 부분 45, 91 %`).

- `common_ed5.ps1`의 git·실행 함수(`Initialize-E8Step`, `Assert-ToolScripts`, `Assert-ToolDiff`, `Assert-E8FixedLists`, `Assert-ToolClosure`, `Invoke-ToolJudge`, `Assert-E8RunCondition`, `Assert-E8RunIdentity`)와 단계 스크립트 본문은 단위 시험이 없다. 구문은 `ps1_lint`(AST)로 확인했고, `Assert-ToolCheckout`·`Assert-ToolDiff`·`Assert-ToolClosure`·`Invoke-ToolJudge`는 `c895bb72`에서 실제 저장소로 읽기 전용 smoke를 돌려 모두 통과했다(`Stop-Step`을 바꿔 끼워 `j9_runs`에 아무것도 쓰지 않음, 출력은 python-expert scratchpad; 결과는 python-expert 보고에 적음: diff 606f8713..c895bb72와 606f8713..b853e107 모두 규칙 안, import 폐포 disjoint, 판정 명령의 작업 폴더·스크립트가 도구 checkout). `Assert-ToolScripts`와 `Assert-E8FixedLists`는 메인 checkout에 도구 커밋이 병합되고 도구 목록이 생긴 뒤에만 돌 수 있어 돌리지 않았다. 단계 전체는 재개 직전 감사와 첫 실행에서 확인된다.
