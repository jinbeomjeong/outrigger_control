## 감사 요약
- **본 결과**: 판 8 판정 대상 결과(census·G′·12a/12b)는 아직 없고 보지 않았다. 읽은 범위는 아래가 전부다.
  - C8 V0 스모크 출력 `ed8_design\smoke_v0_56849248\v0_smoke.jsonl`(2줄, 실행 폴더 밖, 판정 대상 아님)에서 `events`의 꼴만 셌다.
    - 원소 길이, `WARN_ROD_PRESSURE_FALLBACK`·`INFO_ROD_PRESSURE_FAULT_REASON` 사건 수, 사유 문자열의 ':' 분할 수, 사유 토큰이 정해진 6종 안에 드는지 여부만 봤다.
    - 사유 토큰 값 자체는 출력하지 않았다.
- **대상**: T8″ `5955f25b`(ed8-judge2, T8′ 2bf16b31의 자식). C8 `56849248`은 그대로다. 시점은 실행 전(T8″ 재감사)이다.
- **기준 문서**: S8-R(35f9eba8), 결정문 `control_nb1_decision.md`(06b23f91)·`control_nb1_followup.md`(eaf2fccc), stats `stats_nb1.md`(a3ecb47f)·`stats_nb1_addendum.md`(ba74a243), 구현 보고 `t8pp_report.md`(7729d753), 스모크 보고 `smoke_v0_report.md`(2113edee)
- **판정**: 차단 0 / 실행 전 수정 0 / 기록 8
- 앞 재감사의 NB-1·M′-1·M′-2·R′-4는 모두 해소됐다. 결정문 내용(NB-1 (나′), N-A, N-B, 기록 칸, 형상 순서)도 반영됐다.
- **4단계 착수 가능.** 조건은 아래 "4단계 전 메인 할 일" 1~5를 마치는 것이다. 특히 ed8-judge2 잠금, run_config 작성, `check_ed8.ps1` 종료 0, P8-4 기준선이다.

## 앞 항목 해소 확인

| 항목 | 확인 | 근거 |
|---|---|---|
| **NB-1** | 해소 | `aa_pair_verdict`가 `unit_item_verdicts(..., own_setting_items={"J11": "V0"})`를 부른다. 표의 J11을 빼고 `path1.j11_items({**metric, "setting": "V0"})`로 다시 만든다(T8″ jp3_ed8_judge.py `unit_item_verdicts`·`aa_pair_verdict`). 기록 설정 V0이므로 블록이 없으면 "입력 없음"(record)이 되고, 실패에도 판정 불가에도 들지 않는다. `own_setting_items`를 주는 곳은 `aa_pair_verdict` 하나뿐이다. census(`cj_stage`는 `_full_items` 직접)와 G′(`judge_heldout`의 `unit_item_verdicts(...)` 인자 없음)는 바뀌지 않았다. J11 밖의 키를 주면 ValueError다 |
| N-A | 반영 | `V0_ABSENT_KEYS`에 `lock_window_alignment`가 더해져 10개다. 시험 T-3이 있다 |
| N-B | 반영 | group 비교를 row·phase 교체 전에 하고, 다르면 SettingDefect다. 후보가 V0이고 옵션 None인지도 함께 본다(T-4) |
| Q-4 (A) | 유지 | 비구조적 판정 불가(J7 절단)는 지금처럼 NotJudgeable이다(T-5) |
| **M′-1** | 해소 | `census_selection`이 선택 키 결함을 예외로 내지 않고 `basis.setting_defects`에 넣는다. 그래서 census 실패와 함께 있으면 상태는 `failed`다(시험 `test_m1p_census_failure_with_a_selection_mismatch_is_failed`) |
| **M′-2** | 해소(사용자 결정대로) | `has_no_waiver`: 수가 None이거나 키가 없으면 None이 되어 빠지고 기록 실패 (1)이 된다. 수가 있는데 정수가 아니면 `MALFORMED`이고 setting_defect다(gate `has_no_waiver`·`judge_arm_pairs`). P8-5·P8-8 선택자는 bool/None만 돌려주므로 `MALFORMED` 비교의 영향이 없다 |
| **R′-4** | 해소 | `_decision_problems`가 `blocks_used`가 리스트가 아니면 문제로 처리한다. gate_scan의 `missing_key_default_pass`(12b:243)는 이 앞선 검사 때문에 오탐이다 |

## 발견 사항 (기록)

### [기록][R] K-1. NB-1 해석은 봉인 문면을 좁혀 읽은 것이다. 판정서에 해석으로 공개해야 한다
- 결정문 1.4는 두 문장을 해석으로 좁혔다.
  - 10절(spec:346)의 "키·필드 결측 = 판정 불가"를 "그 설정이 만들어야 하는 키"에만 적용한다.
  - 7.4의 "C-J (i) 항목 전부"를 "V0 처리 줄에 정의된 항목 전부"로 읽는다.
- 근거는 판정 도구가 이미 쓰던 436.8 rev16 R16-6 2·RD-10 규칙이다(judge4368_common.py:559-598). 사용자 결정(2026-11-27)으로 T8″에 반영됐다.
- 판정서에 할 일
  - 결정문 후속 4절 공개 문장을 그대로 옮긴다.
  - A/A 바닥에 J9·J11 기여가 없어 $k_N$이 엄해지는 쪽이라는 점(stats Q-1 문장, 부록 개정 단락)을 함께 옮긴다.

### [기록][E] K-2. 새 기록 칸은 판정 상태를 읽지도 바꾸지도 않는다. 다만 같은 함수 안이라 예외가 나면 판정을 잃는다
- **판정 불변 확인**
  - `census_jx`는 `outcome`이 계산된 뒤에 돈다. `outcome`을 바꾸지 않고 새 dict만 만든다. `report["status"]`는 `outcome["basis"]`에서 정해진다.
  - `heldout_jx`·`aa_shape_record`·`aa_j11_states`도 같은 방식이다.
  - 시험 `test_ed8_t8pp_records.py`가 deepcopy 대조로 이를 고정한다.
- **남는 위험**: 기록 계산이 같은 판정 함수 안에서 감싸지지 않고 돈다. 예외가 나면 `main`의 일반 예외 처리로 종료 3이 되어 판정 보고가 쓰이지 않는다. 대상은 `witness_sums`의 `int(opened)`, `effective_shape`의 `float(...)` 등이다.
- **생산자 꼴로 본 도달성**
  - 증인 기록: `two_pressure._d6_witness_record_round`(two_pressure.py:1838-1853)는 `not_opened_rounds`를 `[0]*4` int로, `would_warn`을 bool로 쓴다. 기록이 없으면 `probe_d6_record` None이나 키 없음 쪽으로 가서 따로 센다.
  - 사유 사건은 `_fall_back`이 `INFO_ROD_PRESSURE_FAULT_REASON:{leg}:{reason}` 꼴로만 낸다. reason은 D6·D1·D1_stuck·D2·D3·D4 가운데 하나다(two_pressure.py:1802·1966·1997·2004·2451·3747).
  - 따라서 도달 가능성은 낮다. 기록 칸이 판정을 끄지 않도록 기록 계산을 try로 감싸고 실패를 `record_failures`로 보내는 보강을 다음 판정 도구 개정 때 권한다. 이번에 차단하지는 않는다.

### [기록][R] K-3. 구현자 확인 필요 1: C-D·C-G 단위를 `V0-comparison fail`로 둔 처리
- C-D·C-G 단위는 J 항목이 아니라 V0 격자 비교(`event_output.pass`, Q7-C4)로 실패한다(jp3_ed7_judge.py:1057-1083). 그래서 `unit_info_of`가 붙이는 이름 `V0-comparison fail`은 {J9, J11}과 겹칠 수 없다. stats Q-2 정의("실패 항목 합집합 ⊆ {J9, J11}")를 그대로 적용한 결과이므로 타당하다.
- 귀결: C-G 칸(C-D 소유 단위 포함)의 `jx_only_units`는 구조적으로 0이다. 그 칸의 `F − jx_only ≤ k` 문장은 `F ≤ 0`과 같다.
- 판정서에는 "C-G 칸의 jx_only 0은 J9·J11의 영향이 없다는 뜻이 아니라, 그 칸이 J 항목으로 판정되지 않는다는 뜻"이라고 적는다. 같은 칸의 `j11_opportunity_lines`·사유별 수는 줄 기준이라 의미가 있다.

### [기록][I] K-4. 구현자 확인 필요 2: 사유 토큰 읽기는 생산자 꼴과 맞는다
- 생산자 코드: 위 K-2의 `_fall_back` 꼴. 사유 토큰은 `fallback_reasons`의 `FALLBACK_REASONS`와 정확히 같은 6종이다.
- C8 스모크 실측(V0 2줄)
  - `events`는 `[t, name]` 원소 길이 2의 리스트다.
  - 줄마다 `INFO_ROD_PRESSURE_FAULT_REASON` 사건이 있고, 모두 ':' 3분할이며 토큰은 6종 안에 든다(정해진 종류 4/4).
  - 즉 INFO 사건은 줄 `events`에 남는다(WARN만 거르지 않음).
- 관찰(기록): 스모크 V0 두 줄 모두 다리 네 개의 `WARN_ROD_PRESSURE_FALLBACK`이 있다. V0에는 `lock_window_alignment`가 없으므로 J11과는 무관하다. 이 대체가 A/A J7(새 WARN 이름)에 주는 영향은 같은 V0끼리라 상쇄된다.
- 한계: 사건 목록이 200개에서 잘리면(EVENT_LIST_CAP) 사유가 `unknown`으로 셀 수 있다. 기록 칸이고, J7 절단은 판정 불가로 따로 잡힌다.

### [기록][E] K-5. 스텁 없는 T-1~T-8의 실질
- `test_ed8_t8pp.py`·`test_ed8_t8pp_records.py`에는 `monkeypatch.setattr/setitem`이 0건이다(Grep).
- 봉인 held-out·격자 키와 T-8 `main.jsonl`은 `OUTRIGGER_RECORDS_ROOT`에서 읽는다. 없으면 `assert path.is_file()`로 실패하고 skip하지 않는다(test_ed8_t8pp.py:151).
- 실제 경로 범위
  - T-1·T-2: 생산자 꼴 합성 V0 줄로 `metric_of`, `is_base_pass`, `unit_item_verdicts`, `aa_pair_verdict`, `judge_stage5` main을 끝까지 돈다.
  - T-8: 저장 V0 사건 쌍 22개.
  - 스모크: C8 실제 V0 한 쌍.
- 앞 감사의 실험(저장 V0 30쌍에서 J11 판정 불가 30/30)이 지금은 "입력 없음"으로 바뀌었다(T-8, 스모크).
- T8″ junit
  - 9031건, 실패 2(기존), 오류 0, skipped 134, critical_skipped 0(`test_ed8_|test_ed7_judge|test_ed7_adoption|test_k2_chrono_runner`)
  - `junit_compare_C8_vs_T8pp.txt`: 상태 변화 0
- 남은 스텁: 기존 `test_ed8_judge.py`의 층·순서 논리 시험은 `aa_pair_verdict`를 스텁으로 쓴다. 실제 경로는 위 시험이 따로 덮으므로 문제없다.

### [기록][E] K-6. c877b8cd 중간 오류 2(`No module named 'l1r_variant'`)
- 판단: 판정 도구 결함이 아니라 기존 시험의 순서 의존성이다.
  - `test_k2_chrono_runner._import`(C8 05_tests/unit/test_k2_chrono_runner.py:32-37)가 `02_chrono` 경로를 넣었다가 바로 뺀다. 그래서 import된 모듈이 나중에 하는 지연 import는 같은 작업자에 경로가 남아 있는지에 따라 성공하거나 실패한다.
  - c877b8cd와 T8″의 차이는 판정 도구·기록 시험뿐이다. 이 시험은 C8 junit·T8″ junit에서 통과했다.
- **P8-4 영향(주의)**: 이 시험은 C8에도 있다. P8-4 `-Side run`에서 같은 오류가 나면 "새 실패(오류)"가 되고, 규칙 4절·12절에 따라 멈추고 묻는다(재실행 없음).
  - `worktree_tests.py`에는 xdist 옵션이 없다(Grep). 직렬 실행이면 파일 순서가 고정되어 base·run 결과가 같을 가능성이 높다[추정].
  - 메인 권고: 실행 기록에 이 시험의 성질을 미리 적어 두고, 나오면 "기존 시험 순서 의존" 근거와 함께 사용자에게 묻는다.

### [기록][I] K-7. 스모크가 G′ 꼴 V0 줄을 덮지 못한 것의 무게: 중간 이하
- 판정 경로: V0 A/A의 판정 쪽(`metric_of`·항목·J11 범위)은 twin 사건 이름과 무관하게 줄 값에서 읽는다. twin을 읽는 곳은 층 함수 `stratum_of`(시험으로 덮임)와 job 키뿐이다.
- 생산자 경로: run_v5가 twin `event`·`timing`·`depth_m`·`ramp_s`를 명시한 V0 job에서 무엇을 쓰는지(`event_output.reapproach_starts`, 사건 목록)는 5단계 전에 실제 줄로 본 적이 없다.
  - 결함이 있으면 5단계가 setting_defect·not_judgeable·오류 줄로 닫힌다(잘못 통과하지 않는다). 그러나 1356줄을 돌린 뒤 멈추게 된다.
- 권고(선택, 5단계 전, 4단계와 병행 가능): **G′ 슬롯이 아닌** 명시 twin V0 job 2~3개로 스모크를 한다.
  - 예: RE1bF·FS24·G4, 저장 Fs, 본 위상 offset 0.0, 형상은 기본값 그대로 또는 기본값을 명시한 `depth_m` 0.030·`ramp_s` 0.05.
  - 저장 격자 조건과 같은 본 조건이라 held-out 미관측 조건이 아니다.
  - 스모크 스크립트가 job 키가 `heldout_g_ed8.json` 1356 job에 없음을 먼저 단언해야 한다.
  - G′ 슬롯 조건 자체를 미리 돌리면 5단계 A/A 바닥을 앞서 보는 셈이 되므로 하지 않는다.

### [기록][S·T] K-8. 추적과 SUMS
- 아래 폴더는 SUMS 해시가 모두 맞지만 전부 미추적이다.
  - `t8pp_evidence\`(7항목), `smoke_v0_56849248\`(9항목)
  - 앞 감사에서 본 `keys_seal_41e107e9`, `keys_selection_ed8`, `t8p_evidence`, `p816_prerun_41e107e9`, `impl_report_ed8`, `audit_prerun`
- `audit_prerun\stats_nb1\`은 stats가 파일 2개를 더했다고 적었으므로 SUMS를 다시 써야 한다.
- ed8-judge2는 아직 잠기지 않았다(`worktree_locks` locked 0).

## 남은 생산자 꼴 미시험 경로
| 경로 | 상태 | 처리 |
|---|---|---|
| census 읽기(C-J `metric_of`·`_full_items` 위의 VBN·LSN 줄, C-S `unit_table`, C-D `d_lines_of`, C-G `grid_line_values`) | 시험은 스텁이다. 실제 run_v5 VBN 줄로 돈 적이 없다 | 4단계 `impl_t8`(VBN·VBN0 44줄)·`impl_cases` 출력이 나오면 census 읽기 함수(`identity_defects`, `metric_of`, `unit_item_verdicts`, `jp3_of`, `jx_line_counts`)를 그 줄로 상태만 보는 스모크를 한다. 출력은 실행 폴더 밖에 두고 값은 보지 않는다. 6단계 전에 한다 |
| heldout 읽기 | 같다(VBN 처리 줄 + 5단계 V0 기준) | 위 스모크로 VBN 쪽을 덮는다 |
| 12b decide·judge·four-case(r79 VBKN0 줄) | 실제 r79 판 8 줄로 돈 적이 없다 | 4단계 `l1ref`(r79 L1 줄) 출력 뒤에 `identity_defects`(A-4 스위치 읽기)와 `load_lines` 꼴을 상태만 보는 스모크로 확인한다. 10단계 전에 한다 |
- 위 경로들은 결함이 있으면 종료 2·3으로 닫힌다(잘못 통과하지 않음). 그래서 4단계 착수를 막지 않는다.

## 4단계 전 메인 할 일 (최종)
1. **ed8-judge2 잠금**: `git -C C:\workspace\outrigger_control worktree lock --reason "ed8 T8'' 5955f25b (judge checkout)" .claude\worktrees\ed8-judge2`. 옛 ed8-judge(ecf6c142) 잠금 사유에는 "대체됨(T8″ 5955f25b)"을 남긴다. 이후 판정은 모두 T8″로 한다.
2. **run_config**: `prelaunch_j9\ed8_run_config.json`을 메인 checkout에 만든다(지금 없음).
   - 원본: C8 `run_steps_ed8\ed8_run_config.template.json`
   - `run_commit` = `56849248371b4916e2fe683265e7abffdd6fb8d7`
   - `worktree` = `C:\workspace\outrigger_control\.claude\worktrees\ed8-impl`
3. **check_ed8**: run worktree의 `check_ed8.ps1`이 종료 0인지 본다. 확인 범위는 HEAD·clean·부모 41e107e9·P8-10 범위·03_src tree·numba 위치·고정 입력과 판 8 입력 sha다.
4. **P8-4 두 쪽**(각 25~30분, 시작 전 cpu-scheduler `status.py`로 예약 확인)
   - (a) base
     - `git worktree add --detach .claude\worktrees\ed8-base41 41e107e9`
     - `$env:NUMBA_CACHE_DIR = <runner 폴더>`
     - `full_suite_ed8.ps1 -Side base -Worktree <ed8-base41> -ExpectCommit 41e107e98a5b0e45c3197dbfee46e8dd033eba35 -OutDir <runner 하위 새 폴더>`
   - (b) run: C8 별도 detached checkout(ed8-impl 아님)에서 `-Side run -ExpectCommit 56849248… -BaselineList <a의 existing_failures.txt> -BaselineSha256 <그 sha>`
   - (c) 두 checkout 모두 `.nbi`·`.nbc`가 0인지와 `status --ignored`를 본다.
   - (d) K-6의 순서 의존 시험이 나오면 멈추고 묻는다.
5. **커밋 대상**(4단계 전 권장, 늦어도 6단계 census 전)
   - `ed8_design\`의 `keys_seal_41e107e9\`, `keys_selection_ed8\`(+SUMS), `p816_prerun_41e107e9\`(npz 54개는 LOCAL_ONLY와 백업)
   - `impl_report_ed8\`(SUMS 다시 쓰기), `t8p_evidence\`, `t8pp_evidence\`, `smoke_v0_56849248\`
   - `audit_prerun\`(이 보고와 결정문·stats, `stats_nb1\`·`control_t8p_evidence\` SUMS는 커밋 직전에 마지막으로 쓴다)
   - 커밋 전에 integrity-checker를 거친다(프로젝트 규칙).
6. 4단계 배치: compute-scheduler-expert 배치표를 받는다. 순서는 scope → l1ref → p80 → p816 → p85 → p88 → p815 → t8 → cases다.
7. 4단계 출력 뒤, 관문 판정 전에 할 것
   - M-5 키 존재 점검(구현 보고 표와 `lock_window_alignment`·사유 사건 꼴)
   - "남은 생산자 꼴" 스모크(census·12b 읽기, 상태만)
   - 그 뒤 T8″로 관문을 판정한다(P8-15는 r79 4쌍을 빼고 기록 실패 (1)).
8. (선택, 5단계 전) K-7의 명시 twin V0 스모크.

## 확인 필요
- 없음. 판정서 공개 문장 K-1·K-3은 결정문·stats 초안을 그대로 쓴다.

## 위임 필요
- python-expert(다음 판정 도구 개정 때, 이번 차단 아님): K-2의 기록 계산을 try로 감싸 `record_failures`로 보내기.
- `tools/verif 후보`(python-expert): "판정 함수 안 기록 칸 예외 경로" 검사.
  - 입력: 판정 도구 .py
  - 출력: status 계산 뒤 같은 함수에서 감싸지지 않고 부르는 `record`·`jx`·`shape` 계열 함수 목록
  - 종료 1: 발견 있음

## 검사하지 못한 것
- census·heldout·12b 읽기의 실제 판 8 생산자 줄 실행(위 표, 4단계 출력 뒤)
- G′ 꼴 명시 twin V0 줄의 생산자 출력(K-7)
- `worktree_tests`의 실제 병렬 여부와 K-6 재현(P8-4에서 드러남)

## 실행한 검증
- **인터프리터**: python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`). 이번에는 Chrono-dev를 실행하지 않았다.
- **git(조회만)**: `log`, `diff --stat 2bf16b31 5955f25b`, `diff`(gate·12b·judge), `diff --name-only 56849248 5955f25b -- 03_src 06_analysis`(빈 출력), `git grep`(two_pressure 사유·증인 생산자, verdict_runs `probe_d6_record`), ed8-judge2 `rev-parse`·`status --porcelain --ignored`(전후 비어 있음)
- **verif 도구**
  - `junit_skips`: T8″ junit은 실패 2·오류 0·critical_skipped 0, c877b8cd junit은 오류 2
  - `baseline_check sums`(t8pp_evidence, smoke_v0_56849248): 일치, 미추적
  - `gate_scan`(T8″ 4개): 경고 10, 새 꼴 없음. 12b:243·gate:181·rules:567은 오탐
  - `worktree_locks`(ed8-judge2): 미잠금
- **즉석 명령**: python-dev `-c` 한 줄로 스모크 `events`의 꼴만 셌다. scratchpad `verif-ed8-t8pp\`(source_guard state)는 보고 전에 지웠다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, t8pp_report.md 7729d753…, control_nb1_decision.md 06b23f91…, control_nb1_followup.md eaf2fccc…, smoke_v0_report.md 2113edee…, stats_nb1.md a3ecb47f…, stats_nb1_addendum.md ba74a243…, SHA256SUMS 3f170c9d…, SHA256SUMS 842cb987…, v0_smoke.jsonl 35da6992…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 에이전트 메모리: `audit_pitfalls.md` 같은 항목에 (e) 같은 판정 함수 안 기록 칸의 예외, (f) 순서 의존 시험과 무재실행 관문을 덧붙였다.
- 사용한 스킬: 없음

## 공개(행위 그대로)
- 블라인드(`j9_runs\606f8713\cdry_a1\…`, `prelaunch_j9\ed6_inputs\x11\selection.json`, worktree 사본)는 열지도, Grep·Glob 대상으로 쓰지도 않았다. 상위 폴더도 검색 path로 쓰지 않았다.
- Grep·Glob 범위로 지정한 곳
  - 폴더: `ed8_design\t8pp_evidence`, `ed8_design\smoke_v0_56849248`(Glob `*`), `ed8-judge2\05_tests\unit`(glob `test_ed8_t8pp*.py`)
  - 단일 파일: `test_ed8_t8pp.py`, `stats_nb1_addendum.md`, `~\.claude\tools\verif\worktree_tests.py`, ed8-impl `05_tests\unit\test_k2_chrono_runner.py`
- `git grep`은 ed8-judge2 안의 파일 경로를 직접 지정했다.
- Bash에서 `sed -n`으로 two_pressure.py 줄 범위를 읽었다(조회, 파이프 없음).
- 스모크 V0 줄(판정 대상 아님)은 사건 꼴의 셈만 출력했다.
- 프로세스를 종료하지 않았다. 시험을 돌리지 않았다.
