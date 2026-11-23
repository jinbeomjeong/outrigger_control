## 감사 요약
- 대상·시점·기준 문서: [시점] 실행 전. 판 6 J-P3 보완(436.9) 경로 1 본 실행 직전 감사.
  - 봉인 명세 `06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v6.md`(07a55e17, 개정 14)
  - 정오 1 `jp3_remedy_spec_v6_erratum1.md`(1d4f7539)
  - 정오 2 `jp3_remedy_spec_v6_erratum2.md`(20a60e57)
  - 우선순위는 정오 2 > 정오 1 > 봉인본으로 읽었다.
  - 실행 커밋 aa3e6c4a, worktree `C:\workspace\outrigger_control\.claude\worktrees\ed6-run6`(locked, HEAD aa3e6c4a, 트리 깨끗함). `03_src` tree는 f6bb6033으로 ac3c25a7과 같다.
- 본 결과: 판 6 결과는 아직 없다(`j9_runs/aa3e6c4a/`와 `FIXED_INPUTS_aa3e6c4a.SHA256SUMS`가 없음을 Glob으로 확인).
  - 판정값은 보지 않았다. 열람은 키 이름·건수·정체성 필드로 한정했다.
  - 정체성 필드: `controller_tag`, `lsb_components`, T4h meta 키 이름. 출처는 공개된 본 행인 prelock 755a15d8 T4h와 b1off 40 T4h.
  - 건수: 606f8713 사례·D0·V0 표본 참조 파일의 job 수, `main.jsonl` V0 R12 줄의 `event_output` 키 존재.
  - 606f8713 `j9main_a1/j9_main.jsonl`(판 5에서 이미 본 결과)에서는 job 필드만 읽어 job 집합을 대조했다.
  - 블라인드 경로(`cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`)는 Read·Grep·Glob 어디에도 넣지 않았다.
- **판정: 차단 0 / 실행 전 수정 3 / 기록 9**. 실행을 막는 결함은 없다. 실행 전 수정 1(P6-4 근거 커밋)은 list 단계 전에, 2·3은 확인 단계(step6) 시작 전에 처리하거나 처리 방식을 정하길 권한다.

## 발견 사항 (심각도순)

**[실행 전 수정][I·T] 1. P6-4 전체 시험 근거 폴더 `ed6_design/suite_aa3e6c4a/`가 git에 추적되지 않는다**
- 근거
  - `git status --porcelain`: `?? 06_analysis/02_control/j_p3_cause/ed6_design/suite_aa3e6c4a/`
  - `baseline_check sums …/suite_aa3e6c4a/SHA256SUMS`: `cited_untracked 11`(error). 해시 불일치·누락은 0이다.
  - 정오 2 2-2의 "기존 실패 목록(파일 + sha256)으로 고정…실행 커밋의 P6-4보다 먼저"가 가리키는 파일이 `existing_failures.txt`(eb108f3d)다. 이 파일이 이 폴더에만 있다. 원본도 `~/.claude/runners/outrigger-ed6-suite/`에만 있다.
  - 시각 순서는 맞다: base 06:16~07:05, run 07:05~08:05. 정오 2 커밋 06:03보다 뒤다.
- 실패 시나리오: 판정서가 P6-4 통과와 기존 실패 목록을 인용할 때 커밋으로 고정된 근거가 없다. 러너 폴더나 작업 트리를 지우면 근거가 사라진다.
- 권장 조치: 메인이 이 폴더를 커밋한다(list 커밋과 함께 해도 된다). 폴더의 SUMS는 이미 맞다.

**[실행 전 수정][E] 2. 격자 판정 `fault_reasons`는 키가 없으면 FAULT 0을 통과로 읽는다. 명세 6.6의 key_presence 관문은 실행 단계에 코드 경로로 없다**
- 근거
  - `jp3_ed6_judge.py:694` `if (event.get("fault_periods") or 0) > 0`, 696 `event.get("fault_events")`, 698 `(event.get("gates") or {}).get("fault0") is False`, 700 `row.get("events") or []`
  - 네 키가 모두 없으면 `reasons`가 비어 6.3 (나)의 "192줄 FAULT 0"이 그대로 통과한다. 단위 시험 `test_fault_reasons`·`test_grid_opportunity_allowance_fault_and_warn`(test_ed6_judges.py 363~393)은 키가 있는 줄만 다룬다.
  - `KEY_PRESENCE`(jp3_ed6_judge.py:132~147)는 정의만 있다. Grep 결과 `04_scripts`·`05_tests`·run steps 어디에서도 쓰지 않는다.
  - step6·step7 스크립트에 key_presence 호출이 없다.
  - 명세 6.6 원문: "판정 근거 입력이 없으면 그 단계를 돌리지 않고 판정 불가로 둔다(`key_presence`)".
- 위험 크기(근거 있음): 저장 `v5/main.jsonl`의 V0 R12 사건 줄 481줄에서 `event_output.pass/gates/gates.fault0/fault_periods/fault_events/warnings`와 `events`가 모두 있다. run_v5 사건 줄에서 키가 빠질 가능성은 낮다.
  - 다만 판 6 실행 커밋의 run_v5 격자 줄(twin `event`/`timing`)은 건식 실행이 출력을 만들지 않아 확인하지 못했다. step 5는 사례·T8 줄만 돌려서 격자 키를 미리 보지 않는다.
- 권장 조치(python-expert)
  - 둘 가운데 하나: (가) step6에서 `confirm_b.jsonl`에 `key_presence.py --key event_output.pass --key event_output.gates.fault0 --key event_output.fault_periods --key event_output.fault_events --key events`를 판정 전에 돌려, 종료 0이 아니면 Stop 2. (나) `fault_reasons`가 키 결측을 `NotJudgeable`로 낸다.
  - 합성 시험을 하나 더한다(키 없는 줄이면 판정 불가).

**[실행 전 수정][R·E] 3. 감도 판정(`sens`)에 j9_main의 R15 "나빠짐만 판정" 예외가 없어, probe가 덮는 R15 멈춤 단위가 사실상 판정되지 않는다**
- 근거
  - 명세 6.2: "각 단위를 V0 같은 행·위상과 6.2 j9_main 규칙(읽기 (1)~(3) 포함)으로 판정" / "probe가 덮는 단위 32개…하나라도 V0 대비 실패하면 멈춘다" / "R15는 감도 판정에 기여하지 않는다(두 위상 모두 probe가 덮음)"
  - 명세 7절: "R15의 J1·J2는 V0도 실패하는 기준선이고, 나빠짐만 판정한다"
  - j9main은 `base.r15_worsening`(jp3_ed6_judge.py:409, 449; jp3_j9main_judge.py:573~596, 두 위상 산포 "구분됨")을 센다.
  - `judge_sens`(602~670)에는 이 판정이 없다. `j2_items`(judge_stage1_4368.py:254~266)는 기준이 통과할 때만 J2 실패를 내므로, V0가 실패하는 R15는 sens에서 실패 항목이 생길 수 없다.
- 실패 시나리오: 감도 설정이 R15 최소 힘을 V0보다 뚜렷이 나쁘게 만들어도 sens 멈춤 조건에 걸리지 않고 통과한다.
- 권장 조치: 규칙이 맞다면 `sens`에 설정별 R15 나빠짐 판정을 넣는다(python-expert). 의도가 "sens에서 R15는 단위 항목표만 본다"였다면 정오로 확정한다(control-expert). 아래 확인 필요 1.

**[기록][R] 4. `KEY_PRESENCE["t4h_arrays_12b"]`가 도구가 실제로 요구하는 배열과 다르다**
- 근거: `jp3_12b_judge.py:179~180` `T4H_REV6_ARRAYS`에는 `jp3_r59_end_guard_substeps`가 있다. 353행에서 vbk 팔에 이 배열을 요구한다. KEY_PRESENCE에는 이 이름이 없다.
- 영향: 판정 영향은 없다. 12b 도구가 배열이 없으면 직접 판정 불가로 낸다.
- 명세 6.6: "정확한 배열 이름 목록은…도구가 읽는 이름과 같게 고정하고, 실행 전 감사가 대조한다". 판정서에 차이를 적거나 목록을 고친다.

**[기록][I] 5. P6-4 핵심 범위 패턴이 정오 2 2-2의 범위보다 좁다**
- 근거: `suite_judgement.json`의 `core_patterns`에는 `test_jp3_*`·`test_ed6_*`·`test_run_v5*`·`test_lock_start_b*`·`test_c2*`·`test_extend_start_bound*`만 있다.
  - 바뀐 `03_src` 파일 `check_open_delay.py`·`v5_options.py`의 시험(`test_hydraulics_check_open_delay`, `test_hydraulics_v5_options`)이 빠졌다.
  - step5가 쓰는 `d0_plant_split`, 바뀐 `r79_sensor_screen`의 시험(`test_d0_plant_split`, `test_r79_*`)도 빠졌다.
- 다시 셈: 넓힌 패턴으로 `junit_skips.py junit_run_aa3e6c4a.xml --critical "test_(jp3_|ed6_|run_v5|lock_start_b|c2|extend_start_bound|hydraulics_check_open_delay|hydraulics_v5_options|d0_plant_split|r79_|two_pressure_extend_start)"`를 돌린 결과 `critical_skipped 0`이다.
  - 실패 2(`test_d8x_diag`, `test_record` worktree 경로)와 skip 15는 모두 기준 목록에 있다. 결론은 바뀌지 않는다.
  - `test_x10_rod_fault` 2건 skip(X10_BASE_ROOT 없음)은 기준선에서도 같다. 판정서에 적는다.

**[기록][I] 6. 중심 참조 파일 두 개가 git에 추적되지 않는다(판 5에서 이어진 관행)**
- 근거: V0 `06_analysis/03_hydraulic/coupled/v5/main.jsonl`은 `.git/info/exclude:23`에 걸린다. `…/resume_k1/h8_noise_VB.json`은 추적되지 않지만 ignore도 아니다(ref_check `ref_untracked`).
- 둘 다 sha로 고정돼 있다: `common.ps1` `$FixedInputs` MAIN_JSONL 9ad74990·NOISE_VB 2219ab97, `jp3_fixed_inputs_list.py:229`. 고정 목록에도 들어간다.
- 판정서에 "해시 고정, git 밖"으로 적는다.

**[기록][R] 7. 도구가 스스로 정한 해석: ③ 끔 줄(VBL0·VBKL0)의 태그 동일 검사**
- 근거: `ED6_P3_OFF_TAG = "final_C4G2_LAS_K1_LSB"`(jp3_ed6_judge.py:112, 189). 명세 6.1은 ③ 끔 줄에 "5번만 본다"고 정했다. 도구는 명세보다 엄격하다.
- 실제 꼴: prelock dg3_VBL0·L1_VBL0 T4h meta의 태그가 이 값과 같다. VBL은 `final_C4G2_P3W_LAS_K1_LSB`이고, `lsb_components`는 둘 다 `['A_i','A_ii','B3']`다.
- 통과로 새는 방향이 아니므로 기록이다.

**[기록][R] 8. 격자 기회 줄 수 174를 단언하지 않는다**
- 근거: `judge_grid`(jp3_ed6_judge.py:742·752)는 `opportunities > 0`만 본다. 174는 키 파일 sha(4e80e69b, 도구 상수 126행)로만 고정된다.
- 시험 `test_grid_opportunity_allowance_fault_and_warn`이 174를 확인한다. 판정에는 영향이 없다.

**[기록][R] 9. 문서 표기 어긋남**
- 근거: `prelaunch_ed6.ps1:7` "the main session commits it before step 6"와 `common_ed6.ps1:21`의 `FIXED_INPUTS_RUN8`이 실제 동작과 다르다.
  - 실제로는 step5의 각 부분이 `Initialize-Ed6Step`(-BeforeList 없음)에서 `Assert-FixedList`(common_ed6.ps1:190~212)를 부른다. 따라서 **list 커밋은 step5 v0d0 전에 필요하다**.
  - 파일 이름은 `FIXED_INPUTS_aa3e6c4a.SHA256SUMS`다.
- 메인 세션 권고에 반영했다.

**[기록][S] 10. b1off T4h 40개는 SUMS 목록 밖이고 git에도 없다**
- 근거: `baseline_check sums …/b1off_check/SHA256SUMS`에서 `sums_unlisted 40`(warning, `ed6_probe_a1a2b3_t4h/*.npz`)이 나온다.
- P6-3은 jsonl(cbdb4d28) 해시만 대조하므로 판정 영향은 없다.

**[기록][R] 11. ref_check에서 판 6 문서 기준 `ref_missing`이 남는다**
- 근거: aa3e6c4a 기준 3건이다.
  - `ed6_probe.jsonl`: 명세가 정한 로컬 전용 파일이다(개정 13·14).
  - `v5/main.jsonl`: 짧은 경로 표기이고, 위 6의 ignore 파일이다.
- 8acad1ef 기준 16건은 실행 커밋에만 있는 코드·run steps 경로다. 정오 2 2-3 조건 4대로 판정서는 실행 커밋 경로를 인용한다.

**[기록][I] 12. 경로 2 넘김 누설 0은 허용 사전 1개를 더한 결과다**
- 근거: `leak_run_ed6_r14.json`에서 handoff sha 55c8e92e가 파일 해시와 같다. `leak_p2_ed6_r14_allowed.json`은 leak 0이다.
- 허용 추가 없이 돌린 `leak_p2_ed6_r14_allowed_prev.json`은 `name_leak 1`이다. `allow_added_r14: ['ed6_design']`.
- 넘김은 정오 1·2로 바뀌지 않았다. 판정서에 허용 이름을 적는다.

## 규칙↔도구 대조표

| 규칙(원문) | 도구(path:line) | 결과 |
|---|---|---|
| 정오 1 1-4: `ed6_j9_main` = 판 5 j9_main 388 job에서 설정 이름만 바꿈 | run_v5.py:348~350 | 독립 재계산: 저장 606f8713 j9_main 388 job을 VBJ→VBL, LSJn→LSLn으로 바꾼 집합이 `ed6_j9_main_jobs()`와 같음(True). 설정 VBL 100·LSL 각 72 |
| 정오 1 1-4: `ed6_keys` 184·216·192 | run_v5.py:353~366, 340~344 | sens 184(4설정×46, probe_seen 32), confirm_a 216(4×54, probe_seen 0), grid 192(VBL), sha 3개 일치 |
| 6.2 j9_main J-P3 판정 행 200 | jp3_ed6_judge.py:114, 454~455 | 일치. 다르면 defect, 0이면 판정 불가(345~346) |
| 6.2 감도 104 / 6.3 (가) 56 / (나) 192 | jp3_ed6_judge.py:121~128, 650, 748 | 일치 |
| 6.2 probe가 덮는 32단위는 멈춤만, 군집 k = 2 | 633~637, 593~599 | 일치(clusters n≥2, singles > 2). R15 예외는 빠짐(발견 3) |
| 6.2 J7 예외(감도 4설정, 단독 조건, 첫 `:` 토큰) | 118~119, 522~541 | 일치(시험 test_ed6_judges.py:222~245) |
| 6.3 (나) 기회 허용 1, FAULT 0, V0 실패 18줄은 FAULT·J-P3만, WARN 비판정 | 130, 717~747 | 일치. FAULT 키 결측은 통과(발견 2) |
| 6.5 12a 판정 행 1, VBL 대 VBL0, `--new-t4h`/`--base-t4h` | step8a_dg3_ed6.ps1:42~46, jp3_tjr_judge.py:220, 836~874, 877~910 | **확인: 두 인자가 들어간다**. 정체성은 T4h meta의 `lsb_*`·tag |
| 정오 2 2-1 (iii) 사례 10 | jp3_ed6_judge.py:770, 885~918 | 일치(H-7 = 실패, 헤드 전용 줄 = defect) |
| 정오 2 2-1 (ii) T8 44 | run_v5.py:449~463, jp3_ed6_judge.py:836~882 | 22×{VBL,VBL0} = 44. 대체 없는 짝 0이면 판정 불가 |
| 정오 2 2-1 (i) V0 48, D0-1 8 | step5 v0d0, jp3_ed6_judge.py:768~769 | V0 표본 키 48, D0 저장 64줄 중 D0-1 8(key_presence --where) |
| 정오 2 2-1 (i)-2 P5-1형 33 | step5 p51 | 참조 15/2/1/15 = 33(key_presence), job·`commands_sha256` 모두 있음 |
| 정오 2 2-1 (v) probe 40, cbdb4d28 64자 일치 | step5 probe(Assert-Listed 108행), hash-match 793~829 | 일치. **probe 부분에도 Assert-Listed가 걸린다** |
| 정오 2 2-1 (vi) R14 B3 단독 | test_ed6_harness.py:87~95, 276 | 있음(P6-4에서 통과) |
| 정오 1 1-7 F-5 멈춤 경로 시험 셋 | test_ed6_judges.py:130~146 | margin < −6.92 멈춤, 최대 > 14.21 멈춤, None + V0 표본이면 판정 불가가 모두 있다 |
| 정오 2 2-3 조건 1(단계 시작·끝 정체성, 끝에서 다르면 출력 폐기) | common_ed6.ps1:132~171, 229~241 | 일치(Complete-Step에서 Stop 3, .done 없음) |
| 2-3 조건 2(worktree lock) | `git worktree list` | ed6-run6 locked |
| 2-3 조건 3(데이터 입력 전부 + 머리 `# run_commit`) | fixed_inputs_entries_ed6.txt, jp3_fixed_inputs_list.py:80~95·273~275 | 키 셋·selection·L1 키 둘·V0·2-1 참조·네 L1(--add) 모두 있음. 머리 줄을 쓰고 Assert-FixedList(196~198)가 대조한다 |
| 2-3 조건 4(실행 커밋 경로 인용) | 판정서 단계 | 해당 없음(판정 후) |
| 2-4 표지 `judged:t12_VBL_jp3` | record_gates_ed6.ps1:9~16, common_ed6.ps1:116, 261~271 | 일치(시험 test_ed6_erratum2.py:357, 378) |
| 2-4 Exit-Ed6 자리표시 종료 3 | common_ed6.ps1:61~67 | 시험 test_ed6_erratum2.py:393, 412 |
| 4절 멈춤 0 / 1 / 2 / 3 | common.ps1:304~308, jp3_ed6_judge.py:104~106 | 일치. 상태 순서 실패 > defect > 판정 불가 > 통과(306~313) |
| 6.4 12b P-pred(20000×10, rng 20261125), judge에서 재계산 | jp3_12b_judge_ed6.py:46~51, 121~136, jp3_12b_ppred.py:274~303 | 일치(기록 dict는 JSON 왕복으로 같은 값) |
| 3.4 태그 `_LSB`, lsb 집합 | v5_options.py:54, jp3_ed6_judge.py:111~113, 170~195 | 일치(prelock·b1off meta로 실제 값 확인) |

## 확인 필요
1. (발견 3) 6.2 감도 행의 "6.2 j9_main 규칙"에 판 5 정오 2 2-9.3의 R15 나빠짐 판정(두 위상 산포)이 들어가는지 정해야 한다.
   - 들어간다면: probe가 덮는 R15 단위의 멈춤 조건으로 `sens`가 설정별로 계산해야 한다.
   - 들어가지 않는다면: 정오로 "sens는 R15를 단위 항목표로만 본다"를 확정한다(사용자 또는 control-expert).
2. (발견 2) 6.6 key_presence 관문을 step 스크립트로 둘지, 판정 도구의 결측 처리로 둘지 정해야 한다.

## 위임 필요
- python-expert
  - 발견 2: `jp3_ed6_judge.py:690~703` `fault_reasons`에서 키 결측을 판정 불가로 처리하고 합성 시험을 더한다. 또는 `step6_confirm_ed6.ps1` 31~34행 앞에 key_presence 관문을 넣는다.
  - 발견 3: 확인 필요 1의 답에 따라 `judge_sens`에 설정별 `r15_worsening`을 더하고 시험을 만든다.
  - 발견 4: `KEY_PRESENCE["t4h_arrays_12b"]`에 `jp3_r59_end_guard_substeps`를 더한다.
  - 코드를 고치면 run 커밋이 바뀐다. 그러면 정오 1 1-1·정오 2의 실행 커밋 갱신과 건식 실행 재실행이 필요하다. 그래서 대안으로 step 스크립트 쪽 관문만 넣거나, 판정 도구를 별도 도구 커밋으로 둘지를 함께 정한다.
- 반복 검사 후보 `tools/verif 후보`(python-expert): job 집합 대조. 검사 이름은 "batch job set == stored batch with settings renamed". 입력은 저장 jsonl·이름 대응표·`run_v5.<fn>`이고, 출력은 같음 여부·설정별 건수, 종료 코드는 0 같음 / 1 다름이다. 이번에는 즉석 스크립트로 확인했다.

## 메인 세션 권고
- **list 단계 직후, step5 v0d0 전에** `FIXED_INPUTS_aa3e6c4a.SHA256SUMS`를 커밋한다(발견 9). 같은 커밋에 `ed6_design/suite_aa3e6c4a/`를 넣는다(발견 1).
- step6(확인) 시작 전에 발견 2·3의 처리를 정한다. 처리 없이 진행하려면, 확인 단계 run이 끝나고 판정 도구가 돌기 전에 `confirm_b.jsonl`에 `key_presence.py --key event_output.pass --key event_output.gates.fault0 --key event_output.fault_periods --key event_output.fault_events --key events`를 메인이 돌린다(값은 출력되지 않는다). 종료 0이면 grid 판정을 받아들인다. 다만 run steps는 판정을 바로 잇기 때문에 이 방법은 스크립트를 고치지 않으면 쓸 수 없다.

## 검사하지 못한 것
- 판 6 실행 커밋의 run_v5 출력 줄(ed6_keys 격자·감도, ed6_j9_main)에서 판정 키·T4h 배열이 실제로 나오는지는 확인하지 못했다. 건식 실행이 명령만 기록하고 출력을 만들지 않는다. 대신 다음으로 확인했다.
  - b1off 40줄(e8ddf04e): rows 키 13종이 모두 있다. ③ 기록 결측 10줄은 모두 `head_only_declared` 참 줄이라 6.1 예외에 해당한다. `soil_stop_crawler`가 없는 것은 probe에 S8 행이 없기 때문이다.
  - b1off T4h 40개: `rod_pressure_Pa,t_s,phase,meta_json`이 있다.
  - prelock 12a T4h: VBL에는 `jp3_*` 5종이 있다. VBL0에는 없는데 ③ 끔이라 기대와 맞다. `rod_fault_applied`는 고장 계획 없는 12a라 없다.
  - `main.jsonl` 사건 줄: `event_output.*`가 있다.
  - VBKL·VBKL0의 r79 T4h는 판 6 출력이 아직 없어 보지 못했다.
- 판 5 상속 판정 함수(`judge_stage1_4368.metrics`, `r67` 관문, `Get-RecordToolStop`의 닫힌 목록)는 이전 감사 범위로 보고 다시 전수 확인하지 않았다.
- `jp3_12b_judge.py` decide·judge의 판 5 로직 전체는 판 6에서 덮어쓴 부분만 읽었다.

## 실행한 검증
- 인터프리터: python-dev `python.exe -I -B`(MKL_THREADING_LAYER=TBB)를 PowerShell로 실행했다.
  - 프로젝트 import는 run_v5 job 재계산 1회뿐이다. worktree 경로를 sys.path에 넣었고, `NUMBA_DISABLE_JIT=1`, `NUMBA_CACHE_DIR`(scratchpad), `PYTHONDONTWRITEBYTECODE=1`을 썼다. 실행 뒤 worktree `git status --untracked-files=all`이 비어 있음을 확인했다.
- 도구와 결과
  - `seal_check`(명세·정오 1·2, `--sums keys/SHA256SUMS --rev 8acad1ef --check-tracked`): 종료 0. raw 해시 일치, `-text`, LF, BOM 없음, 인용 15 추적됨.
  - `baseline_check sums` 6목록: keys·prelock·tool_aa3e6c4a·ed6_p2_leak는 0. b1off는 unlisted 40, suite는 cited_untracked 11.
  - `ref_check`(8acad1ef / aa3e6c4a): 발견 11.
  - `placeholder_scan --pattern-set both --allow ED6_RUN_COMMIT --allow ED6_RUN_WORKTREE`(run_steps_ed6 16파일 + config): 종료 0. 허용 2건은 템플릿 파일 안에 있다. 재사용 ps1 3개의 8건은 모두 주석 안의 `<…>` 표기라 거짓 양성이다.
  - `ps1_lint` 16파일(13 + 재사용 3): 종료 0(ast).
  - `junit_skips`(run junit, 넓힌 critical): critical_skipped 0.
  - `key_presence`(b1off rows·T4h, prelock T4h, 참조 jsonl, main.jsonl 사건 줄): 값은 출력하지 않았다.
  - `log_errors`(prelock·suite·b1off): 종료 0.
  - `gate_scan`(판 6 도구 5개): warning 7을 코드로 확인했다. tag 단일 비교 4는 정체성 단언이고, s8 기본값·`decision.get` 기본값·`_phases_at` 경로 등도 거짓 양성이거나 기록용이다. `fault_reasons`의 `or 0`은 도구가 잡지 못했고 코드를 읽어 발견 2로 올렸다.
  - 건식 명령 json(15 종료 코드 모두 0)을 단계별로 펼쳐 읽었다.
  - git: worktree 목록·lock, 커밋 시각, merge-base 96dd7bf2, `03_src` tree id, `check-attr`(향후 출력 경로 `j9_runs/aa3e6c4a/**`, FIXED_INPUTS, suite 폴더 모두 `-text`).
- 만든 뒤 지운 파일: scratchpad `auditor-ed6prerun\`(guard.json, dry_dump.py, jobset.py, meta_keys.py, meta_tag.py, seal/ref/ph/lint/gate .md). 폴더째 삭제했다.
- 메모리: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 일반 함정 1항목을 더하고 MEMORY.md 색인을 갱신했다.
- 쓰기 규칙 위반 1건: Bash 파이프(`git status … | head`)를 한 번 썼다. 조회만 했고 Suspended 자식은 남지 않았다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v6.md 07a55e17…, jp3_remedy_spec_v6.md.sha256 e216a6ab…, jp3_remedy_spec_v6_erratum1.md 1d4f7539…, jp3_remedy_spec_v6_erratum1.md.sha256 b3cdd191…, jp3_remedy_spec_v6_erratum2.md 20a60e57…, jp3_remedy_spec_v6_erratum2.md.sha256 80a02c2e…, jp3_rev6_p2_handoff_ed6.md 55c8e92e…, ed6_run_config.json e3be7d60…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
