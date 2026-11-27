## 감사 요약
- 본 결과: 판 8 판정 대상 결과(census·G′·12a/12b)는 아직 없고 보지 않았다. 아래는 과거 판에서 이미 본 자료와 구현 관문 자료를 읽은 범위다. 판정값은 출력하지 않았다.
  - **저장 V0 `06_analysis\03_hydraulic\coupled\v5\main.jsonl`**(판 5~7에서 본 행, O8-1)
    - V0 줄 100개 가운데 30쌍을 T8′의 실제 A/A 읽기 경로에 넣었다.
    - 출력은 결과 종류(bool을 돌려줬는지, 어떤 예외인지)와 판정 불가 항목 이름뿐이다.
    - V0 줄에서 키가 있는지만 셌다.
  - **41e107e9 P8-16 사전 실행 `p816.jsonl`**(L2_impl 팔): 키가 있는지만 세고, 최상위 `ed8_settings`의 잎 타입 꼴만 봤다.
- 대상: T8′ `2bf16b31`(ed8-judge2, T8 ecf6c142의 자식), C8 `56849248`은 바뀌지 않았다. 시점은 실행 전(T8′ 재감사).
- 기준 문서: S8-R(35f9eba8), 해석 결정문 `control_t8p_decisions.md`(e89692cf), 구현 보고 `t8p_report.md`(77d126c9), 앞 감사 `verif_c8_t8.md`(ebe74d67)
- 판정: **차단 1 / 실행 전 수정 4 / 기록 7**
- 앞 감사 항목은 B-1·B-2·B-3·M-1·M-2·M-4·R-2가 해소됐다. M-3·M-5는 메인 몫으로 남는다.
- 새 차단 NB-1이 있다. 5단계 A/A가 실제 V0 줄에서 모든 쌍 판정 불가가 되어, 5단계 판정이 구조적으로 불가하다.
- **4단계 착수: 규칙 문면상 불가**(spec:200 "3단계 감사 차단 > 0이면 멈춤").
  - NB-1은 5단계 판정 코드의 결함이다. 4단계 관문 판정 코드(gate judge, `cases`, `l1ref`)에는 남은 차단이 없다.
  - 그래도 NB-1을 고치면 같은 모듈 `jp3_ed8_judge.py`가 바뀐다. 그러면 4단계 판정과 census·G′ 판정이 서로 다른 판정 커밋에서 이뤄진다(11.2 단일 T8).
  - 그래서 **T8″(NB-1 수정)과 재감사 차단 0 뒤에 4단계를 시작하기를 권한다.**
  - 4단계 실행만 먼저 띄우는 분리는 사용자 결정 사항이다(확인 필요 1).

## 발견 사항 (심각도순)

### [차단][E·R·I] NB-1. 5단계 A/A가 실제 V0 줄에서 모든 쌍 판정 불가 → `stage5`는 항상 not_judgeable
- **근거**
  - 규칙 7.4(spec:303): "V0($o''$)를 처리, V0($o$)를 기준으로 **C-J (i) 항목 전부**로 판정". C-J (i)에는 J1~J11이 들어간다(spec:232).
  - 판정 경로: `jp3_ed8_judge.aa_item_fail`은 후보 V0 줄을 처리 라벨 `VB`로 판정한다(T8′ jp3_ed8_judge.py `aa_item_fail` → `unit_item_verdicts`). 판정 불가 항목이 하나라도 있으면 `NotJudgeable`을 던지고, `slot_inputs`를 거쳐 `judge_stage5` 전체가 not_judgeable이 된다.
  - J11 조건: `judge4368_common.assess_j11`(judge4368_common.py:578-597)에서 멈춤 설정 `VB`는 `lock_window_alignment` 블록이 없으면 `NOT_JUDGEABLE`이다.
  - 생산자 조건: 이 블록은 `hydraulics.lock_window_follows_plant`가 켜진 수력 옵션 경로에서만 쓰인다(verdict_runs.py:880). V0는 `options_of("V0")[1]` = None이다(run_v5.py:123, 결정문 1.2·1.3 "hydraulic_options = null").
  - 키 존재 실측
    - 저장 main.jsonl V0 줄: `lock_window_alignment` 0/100
    - 41e107e9 사전 실행 L2_impl 줄(판 8 생산자): `lock_window_alignment` 27/27
    - 즉 C8 V0 줄에도 이 블록이 없을 것이다(구조적). 판 8 처리 줄에는 있다.
  - 실제 경로 실험(스텁 없음, Chrono-dev, T8′ 코드, 저장 V0 30쌍)
    - `aa_item_fail` → `jp3_ed8_judge.NotJudgeable` 30/30
    - 판정 불가 항목 이름: `J11` 30/30, `S8 SA-4` 1/30
    - `is_base_pass`는 bool 30/30, `no_reference` 0
  - 시험이 놓친 이유: `test_stage5_main_end_to_end_with_the_real_identity`를 포함한 stage5 시험이 `ed7.metric_of`·`ed8.is_base_pass`·`ed8.aa_item_fail`을 스텁으로 바꿨다(test_ed8_judge.py:227-234). 구현 보고 2절도 "A/A 항목 판정은 아직 스텁"이라고 밝혔다.
- **실패 시나리오**: 5단계 V0 1356줄을 돌린 뒤 `stage5`가 종료 2(not_judgeable)로 끝난다. `ho_k_selection`을 동결할 수 없어 S8-C·8단계로 갈 수 없다. 결과가 나온 뒤에 도구·해석을 바꿔야 한다.
- **권장 조치**
  1. 해석 결정(control-expert, 통계 영향은 stats-design-expert): A/A에서 처리 쪽이 V0인 줄의 J11을 어떻게 볼지 정한다.
     - 후보 (가): V0에는 입력이 없으므로 J11은 A/A 해당 없음(기록)으로 둔다.
     - 후보 (나): J11 입력 없음을 A/A 실패로 보지 않는 기록 설정 라벨(`V0` 쪽 규칙)로 판정한다.
     - 어느 쪽이든 A/A 바닥에 J11 기여가 빠진다. G′ 처리(VBN)는 J11을 센다. 이 비대칭 때문에 $k$가 낮아지는 쪽이므로 공개 문장이 필요하다.
     - SA-4 판정 불가(저장 S8 1쌍)가 G′ 슬롯(격자 사건 행)에서 생길 수 있는지도 같이 정한다. [추정] G′ 원천에는 S8 행이 없다.
  2. T8″(python-expert): 결정대로 구현한다. 그리고 **스텁 없이** 생산자 꼴 V0 줄 두 개(`lock_window_alignment` 없음, T4h 없음)로 `aa_item_fail`과 `judge_stage5`를 끝까지 돌리는 시험을 넣는다.
  3. 판단 근거를 넓히려면 메인 세션 권고 3(C8 V0 한 줄 스모크)을 함께 한다.

### [실행 전 수정][E] M′-1. 선택 사용 키 검사 실패가 census 판정 실패를 가린다(상태 순서)
- **근거**: `judge_census`는 `selection_units_checked`(기록 항목)에서 `SettingDefect`를 *예외로* 던진다(T8′ jp3_ed8_judge.py `judge_census`, 단계 계산 뒤·`census_outcome` 전). 그러면 `main`이 `_stopped`로 보고를 갈아 끼워 단계별 실패 근거가 사라지고 상태가 setting_defect가 된다.
- **규칙 10절(spec:338)**: 판정 실패 > setting_defect.
- **도달 가능성**: 낮다. 선택 파일 sha가 고정돼 있고, 단위 job은 같은 census 키 줄에서 오므로 18이 결정적으로 맞는다.
- **권장 조치**(python-expert, T8″에 함께): 예외 대신 `basis["setting_defects"]`에 넣어 계산된 실패와 함께 결합한다. 시험: census 실패 + 선택 키 불일치 = `failed`.

### [실행 전 수정][R] M′-2. P8-15 "읽지 못한 쌍"에 waiver 수가 정수가 아닌 경우까지 넣었다(구현자 확인 필요 1)
- **근거**
  - `has_no_waiver`(gate:324-333)는 키 결측과 비정수를 모두 None으로 돌려준다. 그러면 `unread` → `UNREAD_PAIRS_LEFT_OUT`(gate:102-106·373-378) 경로로 가서 "(1) 3.8 record key missing"으로 기록된다.
  - 시험 `test_p815_waiver_count_that_is_not_an_integer_is_unread`가 이 동작을 고정한다.
  - 규칙 10절(spec:345): 기록 실패 (1)은 "기록 키 **결측**"이다. "목록 밖 문제는 입력 결함(setting_defect)".
  - 사용자 결정 (가)의 "읽지 못한 쌍"은 B-1 근거(r79 줄의 기록 결측)를 가리켰다.
- **판단**: 비정수 값은 결측이 아니라 형식 결함이므로 명세상 setting_defect가 맞다. 지금 구현은 범위 밖이고, 기록 문구("missing")도 사실과 다르다. 도달 가능성은 낮다(생산자가 int로 쓴다).
- **권장 조치**: 결측(`ed8_record`·`twist_waiver` 없음)만 빼서 기록 실패 (1)로 두고, 비정수는 setting_defect로 나눈다(T8″). 아니면 사용자가 지금 범위를 확인한다(확인 필요 2).

### [실행 전 수정][I] M′-3. 5단계 V0 정체성 기대값을 C8 생산자 줄로 확인한 적이 없다
- **근거**
  - 결정 1.3의 `controller_tag == final_C4G2_LAS_K1`(키 없으면 문제)은 생산자 함수 `plant_options_record(None, config)` 시험으로 확인했다(`test_ed8_t8p.py`).
  - 저장 main.jsonl V0 줄에는 `controller_tag`가 없다(결정문 A-3 실측). 4단계 C8 출력 중에는 run_v5 V0 줄이 없다(t8 = VBN·VBN0, p80·p8x = 프로브 팔).
- **실패 시나리오**: 실제 C8 V0 줄의 태그나 키가 함수 시험과 다르면, 1356줄을 돌린 뒤 5단계가 setting_defect가 된다.
- **권장 조치**: 메인 세션 권고 3(C8에서 저장된 V0 job 하나를 실행 폴더 밖에서 스모크로 돌리고 정체성과 A/A 경로 확인).

### [실행 전 수정][I] M′-4. M-3·M-5는 메인 몫으로 남아 있다
- C8 run steps는 바꿀 수 없으므로 T8′ 범위 밖이다.
- **M-3**: 41e107e9 base와 C8 run의 P8-4.
  - `worktree_tests.py`는 부모 환경을 물려받는다(`pytest_environment`, worktree_tests.py:498-510, 빼는 변수는 PYTHONPATH·PYTEST_* 셋뿐). 그래서 실행 전에 `$env:NUMBA_CACHE_DIR`를 지정하면 하위 pytest까지 전달된다. 시험 코드가 이 변수를 다시 덮어쓰는지는 확인하지 않았다.
- **M-5 추가안**: 구현 보고의 표가 타당하다. 아래 둘을 더한다.
  - run_v5 판 8 줄(impl_t8, census, G′ VBN)에 `lock_window_alignment`. J11 입력이고, 41e107e9 L2_impl에서 27/27 있다.
  - 5단계 V0 줄에서 `lock_window_alignment`가 **없음**. NB-1 결정의 전제다.

### [기록]
- **R′-1** 앞 감사 항목 해소 확인
  - **B-1**: `UNREAD_PAIRS_LEFT_OUT={"p815"}`, 기록 실패 (1)을 공개한 뒤 남은 쌍 ≥ 20(gate:370-378). P8-5·P8-8은 그대로 판정 불가.
    - 시험 `test_b1_p815_r79_pairs_are_left_out_and_recorded`, `…needs_20_pairs…`가 r79 생산자 꼴(job = `r79_key`·`setting`, T4h 하위 폴더)로 T8′ junit에서 통과했다.
  - **B-2**: `heldout_judgement`가 `first_aliases`를 2차 별칭·셈 전에 빼고, 목록이 없으면 `RuleInputError`를 낸다(rules:542-553). 시험 `test_b2_first_aliases_are_left_out_at_stage_8[0-True]`·`[20-False]`·`…without_first_aliases…` 통과.
  - **B-3·A-5·M-2**: `v0_identity_problems`, 줄 단위 예외 처리, `main`의 판 7 예외 대응 확인. 다만 실제 V0 줄의 A/A 경로는 NB-1.
  - **R-2·A-4**: 최상위 `ed8_settings` 비교와 r79 스위치 비교.
    - 41e107e9 L2_impl 줄 `ed8_settings`의 잎 타입 꼴은 `ED8_SETTINGS_EXPECTED`와 같다: int `short_run_exit_samples`, float 쌍 리스트 경고 범위, bool·float.
    - 사전 실행 팔의 δ는 None이다. PSW 끈 팔이라 예상대로다.
  - **M-1**: 생성기 `ed8_selection_keys.py`, 파일 sha 3f3753d9가 고정 상수와 같다. 구조는 jobs 23(VBN 21·VBNslow 1·LSN4 1), 기대 단위 18(C-J 11·C-S 1·C-D 0·C-G 6), 단위 아닌 줄 1, census 밖 4, r79 건너뜀 P8-14 13이다. 설정까지 맞춰 대조하고, 0건이거나 기대와 다르면 setting_defect다. 재생성 시험은 통과했고 skip은 없다.
  - **M-4·F-1**: `four-case`가 `jp3_12b_judge.case_of`로 통일됐다. all이 decision `p_pred` 입력과 다르면 setting_defect이고, `k_allow`는 다시 계산하지 않는다.
- **R′-2** 결정문의 5단계 상태 순서가 반영됐다(`judge_stage5`).
  - 순서: 정체성(오류 줄 제외) → setting_defect, 완결성(A-1: 파일 정확히 3개, `heldout_v0_jobs`와 1:1) → not_judgeable. 둘 중 하나라도 있으면 선택을 계산하지 않고 $k$도 동결하지 않는다.
  - 시험 `test_stage5_identity_problem_is_a_setting_defect_and_k_is_not_frozen`, `…identity_and_completeness_together…` 통과.
- **R′-3** 구현자 확인 필요 2(5단계 오류 줄): 오류 줄에는 정체성을 적용하지 않고, `slot_inputs`에서 그 단계 전체를 not_judgeable로 한다.
  - 규칙 6.2 (바) "그 단계 판정 불가"와 같다.
  - 귀결: aa2·aa3를 무조건 돌리므로, 쓰지 않는 후보 줄의 오류 하나도 5단계를 판정 불가로 만든다(`slot_inputs`는 결정 뒤 후보의 오류에도 예외를 낸다). 규칙 문면대로이므로 판정서에 적는다.
- **R′-4** `four-case` `_decision_problems`(12b_judge_ed8.py:241)는 `blocks_used`가 없으면 `[]`로 넘어간다(gate_scan `missing_key_default_pass`).
  - 기록 도구이고, all과 decision 입력 대조(b4 필드)가 b4 누락을 잡는다.
  - 다만 `four_case_vbkn0_lines`가 빈 채로 "written"이 될 수 있다. `blocks_used` 키가 없으면 setting_defect로 하기를 권한다(낮음).
- **R′-5** gate_scan 나머지 경고는 오탐이다.
  - `tag_single_compare` 6건: 설정 이름·자체 라벨 비교이고, 0건이면 기회 0이 되어 판정 불가로 닫힌다.
  - `row_value_path_no_base` gate:179: `.done`의 절대 folder이고, 상대 경로면 setting_defect로 닫힌다.
  - `empty_selection_sum_pass` rules:567: 0이면 해당 없음, 합계 0이면 판정 불가로 처리한다.
- **R′-6** P8-11: `git diff --name-only 56849248 2bf16b31`는 04_scripts 판정 도구 12개와 05_tests뿐이다. 03_src·06_analysis 변경은 0이다. `ed8_selection_keys.py`는 `JUDGE_MODULES`에 추가됐다(run_path 시험 통과).
- **R′-7** 추적·SUMS
  - `keys_selection_ed8\`(SUMS 1항목 일치), `t8p_evidence\`(SUMS 4항목 일치), `keys_seal_41e107e9\`, `audit_prerun\`이 모두 미추적이다(ignore 아님).
  - `junit_diff_*_vs_T8p.txt`는 전체 건수 한 줄씩뿐이다(상태 변화 목록 없음). 그래서 새 실패·새 skip 0은 `junit_skips`로 다시 확인했다(실패 2 기존, skipped 134, critical_skipped 0).
  - ed8-judge2는 아직 잠기지 않았다(`worktree_locks`: ed8-judge2 unlocked, ed8-impl locked).

## 확인 필요
1. NB-1을 고치기 전에 4단계 **실행**만 먼저 띄울지(규칙 4절 3단계 멈춤 조건의 예외). 권고는 T8″ 뒤에 착수다.
2. M′-2: P8-15 비정수 waiver 수를 기록 실패 (1)(지금)로 둘지, setting_defect(명세 10절 문면)로 둘지.
3. NB-1: 5단계 A/A에서 V0 처리 줄의 J11(및 S8 SA-4) 취급(control-expert와 stats-design-expert).

## 위임 필요
- **control-expert**: NB-1 해석 결정문(1~3절 꼴로 근거 줄·공개 문장 포함).
- **stats-design-expert**: A/A 바닥에서 J11이 빠지는 데 따른 $k_N$ 방향과 공개 문장.
- **python-expert(T8″, ed8-judge2 위 새 커밋, C8 불변)**
  - NB-1 결정 구현과 **스텁 없는** 생산자 꼴 V0 A/A 시험
  - M′-1
  - M′-2(결정대로)
  - R′-4(선택)
  - 전체 시험(새 실패·새 skip 0), P8-11 시험
- **verif-protocol-auditor**: T8″ 재감사.

## 메인 세션 권고 (4단계 전 할 일)
1. T8″ 커밋, 재감사 차단 0, 그 다음 ed8-judge(또는 새 worktree)를 T8″에 잠근다. ecf6c142 잠금 사유는 옛 T8이므로 판정 checkout이 바뀐 사실을 lock 사유에 적는다.
2. `prelaunch_j9\ed8_run_config.json`(지금 없음)을 템플릿으로 만든다.
   - `run_commit` = `56849248371b4916e2fe683265e7abffdd6fb8d7`
   - `worktree` = `C:\workspace\outrigger_control\.claude\worktrees\ed8-impl`
   - 그 다음 run worktree의 `check_ed8.ps1`이 종료 0인지 본다.
3. (권고, M′-3·NB-1 근거) C8 V0 스모크 1줄
   - C8 checkout(ed8-impl, 또는 같은 커밋의 별도 checkout)에서 main.jsonl에 이미 있는 V0 job 하나를 `run_v5`로 runner 폴더(`~/.claude/runners/outrigger-ed8/...`, `j9_runs` 밖)에 돈다.
   - 볼 것: `controller_tag`, `V0_ABSENT_KEYS`, `hydraulic_options`·`hydraulics_record` null, `lock_window_alignment` 없음. 그리고 T8″ `aa_item_fail` 경로를 스텁 없이 한 번 통과하는지.
   - 실행 폴더 밖에 두므로 판정 출력이 아니다. 끝나면 run worktree에 `.nbi`·`.nbc`가 0인지 확인한다.
4. P8-4
   - `git worktree add --detach .claude\worktrees\ed8-base41 41e107e9`
   - `$env:NUMBA_CACHE_DIR`를 runner 폴더로 지정한 뒤 `full_suite_ed8.ps1 -Side base -ExpectCommit 41e107e98a5b0e45c3197dbfee46e8dd033eba35`
   - `-Side run`은 C8 별도 detached checkout에서 base 목록 sha를 주고 돌린다.
   - 각 25~30분이고, 시작 전에 cpu-scheduler `status.py`로 예약을 확인한다.
   - 끝난 뒤 두 checkout 모두에 `.nbi`·`.nbc`가 없는지 본다.
5. **커밋 대상**(4단계 전, 6단계 census 전까지)
   - `ed8_design\keys_seal_41e107e9\`
   - `keys_selection_ed8\`(+SUMS)
   - `p816_prerun_41e107e9\`(npz 54개는 LOCAL_ONLY와 백업에 넣는다)
   - `impl_report_ed8\`(SUMS 다시 쓰기: T8 증거 5개 미등재)
   - `t8p_evidence\`
   - `audit_prerun\`(이 보고 포함, 폴더 SUMS는 커밋 직전에 마지막으로 쓴다)
   - control 근거 스크립트를 `audit_prerun\control_t8p_evidence\`로 옮긴 것
6. 4단계 출력 뒤 M-5 키 존재 점검(구현 보고 표 + M′-4 두 키)을 한 다음 관문 판정을 한다.

## 검사하지 못한 것
- `jp3_12b_judge_ed8` 12b decide·judge 본 경로와 `jp3_tjr_judge_ed8`의 생산자 꼴 실행
- census(C-J·C-S·C-D·C-G) 읽기 경로의 생산자 꼴. 시험에서는 `metric_of`·`_full_items`·`grid_line_values`·`d_lines_of`·`unit_table` 등이 스텁이다. 4단계 `impl_t8` 줄로 스모크하기를 권한다.
- C8에서 생산된 V0 줄 자체(스모크 권고 3)
- 시험 코드가 `NUMBA_CACHE_DIR`를 다시 정하는지

## 실행한 검증
- **인터프리터**
  - python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`): verif 도구, source_guard
  - Chrono-dev `python.exe -I -B`(`PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`=scratchpad): T8′ 모듈을 불러 저장 V0 쌍으로 실험(`aa_probe.py`·`aa_items.py`), `ed8_settings` 타입 꼴(`ed8set_types.py`)
- **git(조회만)**: `log`, `diff --stat`·`diff`(T8 대 T8′의 rules·gate·judge, run_path 시험), `diff --name-only 56849248 2bf16b31`, ed8-judge2 `status --porcelain --ignored`(감사 전후 모두 비어 있음)
- **verif 도구**
  - `gate_scan`(T8′ 5개): 경고 9, 모두 판독(R′-4·R′-5)
  - `junit_skips --critical "test_ed8_|test_ed7_judge|test_ed7_adoption"`(T8′ junit): 실패 2 기존, critical_skipped 0
  - `baseline_check sums`(keys_selection_ed8, t8p_evidence): 일치, 미추적
  - `key_presence`(41e107e9 L2_impl, 저장 main.jsonl V0)
  - `worktree_locks`(ed8-judge2·ed8-impl): 종료 0, ed8-judge2는 미잠금
- **해시**: 선택 키 파일 = 3f3753d9…(고정 상수와 같음)
- **즉석 스크립트**: scratchpad `verif-ed8-t8p\`에 썼고 보고 전에 폴더째 지웠다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, control_t8p_decisions.md e89692cf…, t8p_report.md 77d126c9…, verif_c8_t8.md ebe74d67…, selection_keys_ed8.json 3f3753d9…, SHA256SUMS 39d792dd…, SHA256SUMS 912eb29c…, census_keys_ed8.json 278b332f…, heldout_g_ed8.json a18b5818…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 에이전트 메모리: `audit_pitfalls.md` 앞 항목에 (d) "기준 줄을 처리 라벨로 판정하는 A/A의 입력 비대칭"을 덧붙였다.
- 사용한 스킬: 없음

## 공개(행위 그대로)
- 블라인드(`j9_runs\606f8713\cdry_a1\…`, `prelaunch_j9\ed6_inputs\x11\selection.json`, worktree 사본)는 열지도, Grep·Glob 대상으로 쓰지도 않았다. 상위 폴더도 검색 path로 쓰지 않았다.
- Grep·Glob 범위로 지정한 곳
  - 폴더: `ed8_design\audit_prerun`, `ed8-judge2\04_scripts\04_hydraulic\coupled`(`*.py` 또는 파일 지정), `ed8-judge2\05_tests\unit\test_ed8_judge.py`, `~\.claude\tools\verif\worktree_tests.py`
  - 단일 파일: `t8p_evidence\junit_T8p_2bf16b31.xml`
- `Test-Path`는 블라인드가 아닌 단일 경로 2개에 썼다: `prelaunch_j9\ed8_run_config.json`, `j9_runs\56849248`.
- `git ls-files --error-unmatch`를 인용 파일 2개에 직접 지정해 돌렸다.
- PowerShell `git worktree list --porcelain` 출력을 `Select-String`으로 거른 적이 1번 있다(Bash 파이프 아님).
- 저장 V0(main.jsonl)는 이미 본 자료(O8-1)다. 판정값은 출력하지 않았고, 결과 종류·항목 이름·키 존재 수만 출력했다.
- 프로세스를 종료하지 않았다. 시험을 병렬로 돌리지 않았다.
