# 436.9 판 8 T8″ 구현 보고 (재감사 NB-1·M′-1·M′-2·R′-4와 기록 칸)

## 요약
- **T8″는 `5955f25baa2bc0ebc8d7587747752d46def8cbb4`입니다.** `ed8-judge2` 브랜치, T8′ `2bf16b31`의 자식입니다.
  - 처음 커밋한 c877b8cd를 기록 칸 추가로 amend해서 이 sha가 됐습니다.
  - C8 `56849248`과 ed8-impl은 바꾸지 않았습니다.
  - T8′ 대비 diff는 `04_scripts/04_hydraulic/coupled`의 판정 도구 3개와 `05_tests/unit` 4개(새 시험 파일 2개 포함)뿐입니다.
- 반영한 것
  - 차단 NB-1: control 결정문 6절 그대로.
  - M′-1, M′-2(사용자 결정), R′-4.
  - 기록 칸(판정 불변): stats Q-2·Q-3 (1)(2)와 control 후속 2.3·3.3.
- **전체 단위 시험(T8″)**
  - 결과: 2 실패, 8895 통과, 134 건너뜀.
  - 두 실패는 기존 실패입니다(`test_hydraulics_flow_limit_run`, `test_d8x_diag`).
  - T8′·C8 junit과 비교하면 상태 변화 0, 새 건너뜀 0, 새 시험 중 미통과 0입니다. P8-11 시험도 포함했습니다.
- 판 8 결과에는 판정 도구를 돌리지 않았습니다(결과가 없음).

## 1. 반영 내용

### NB-1 (control NB-1 결정 6절)
1. `unit_item_verdicts(..., own_setting_items=...)`
   - `None`이면 census·G′ 경로이고, 바뀌지 않습니다.
   - `{"J11": "V0"}`을 주면 표의 J11 항목을 빼고 `judge_stage1_4368.j11_items({**metric, "setting": "V0"})`로 다시 만듭니다. `stop`은 실패, `not_judgeable`은 판정 불가, `record`는 `own_setting_records`로 갑니다.
   - J11 외 항목을 주면 ValueError입니다.
2. 상수 `AA_OWN_SETTING_ITEMS = {"J11": "V0"}`, `AA_ITEM_SCOPE`.
3. `aa_pair_verdict` → `{"fail", "j11_state"}`. `aa_item_fail`은 이 함수의 bool 래퍼입니다.
   - 전제: 후보가 `job.setting == "V0"`이고 `hydraulic_options is None`이어야 합니다. 아니면 SettingDefect.
   - N-B: group이 다르면 SettingDefect `"A/A pair groups differ"`. row·phase를 바꾸기 전에 비교합니다.
   - 판정 불가 항목이 남으면 지금처럼 NotJudgeable입니다. Q-4는 (A) 유지(T-5).
4. `slot_inputs` 후보에 `aa_j11_state`를 둡니다. stage5 report에 `aa_item_scope`와 `aa_j11_states`(결정 쌍의 J11 상태 분포)를 둡니다.
5. N-A: `V0_ABSENT_KEYS`에 `lock_window_alignment`를 더했습니다(10개).

### M′-1
- `census_selection`: 선택 키 검사가 실패하면 예외를 내지 않고, 그 문장을 `basis.setting_defects`에 넣고 계산을 계속합니다.
- 그래서 census 실패가 함께 있으면 상태는 failed입니다(시험 있음).

### M′-2 (사용자 결정 2026-11-27)
- P8-15 waiver 수가 **결측**(None 또는 키 없음)이면 그 쌍을 빼고 기록 실패 (1)로 둡니다.
- 수가 **있지만 정수가 아니면**(float·str·bool) `MALFORMED`로 표시하고 setting_defect입니다. 보고에 `malformed` 목록을 둡니다.
- 시험 `test_p815_waiver_count_that_is_not_an_integer_is_unread`는 아래 두 시험으로 바꿨습니다.
  - `…_is_a_setting_defect[1.0, "0", True]`
  - `…_missing_is_left_out[None, 키 없음]`

### R′-4
- `four-case` `_decision_problems`: `blocks_used`가 리스트가 아니면(없음 포함) 문제로 넣고, 결과는 setting_defect입니다.

### 기록 칸 (판정 불변, 기록만)
- stats Q-2 (1)
  - `jx_record`·`jx_line_counts`: 병합 단위 기준이며, G′는 1차·2차 별칭을 뺀 뒤에 셉니다.
    - `jx_only_units`: 기준 통과 ∧ 처리 실패인 구성원의 실패 항목 합집합이 비어 있지 않고 {J9, J11}의 부분집합인 단위.
    - `jx_any_units`, `j9_judged_lines`, `j11_opportunity_lines`, `j11_not_judgeable_lines`.
  - 기록 문장 `jx_statement`: `F − jx_only_units ≤ k` 여부. "판정 아님"을 명시합니다.
  - 칸 위치: census는 `records.jx.cells["<칸> <층>"]`(k = 0), G′는 `records.jx.cells[<층>]`(k = 재계산된 층 k).
- control 후속 2.3 (같은 칸에 추가)
  - `j11_opportunity_by_reason`: `INFO_ROD_PRESSURE_FAULT_REASON` 사유 토큰 D1·D1_stuck·D2·D3·D4·D6·unknown. 한 줄은 대체 다리의 사유마다 한 번씩 셉니다.
  - `probe_d6_witness`: 다리별 `not_opened_rounds`·`would_warn` 합. 기록이 없거나 꼴이 다른 줄은 따로 셉니다(0으로 읽지 않음).
- stats Q-3 (2)와 control 3.3
  - `ho_k_selection`에 `aa_shape_record`를 둡니다.
  - 대상: 기준이 통과한 슬롯의 결정 쌍(state pair) 가운데 형상이 다른 쌍.
  - 분류는 `SHAPE_SEVERITY` 상수 한 곳에 둔 지배 순서입니다. 가혹 = depth_c ≥ depth_o ∧ ramp_c ≤ ramp_o이고 하나 이상 엄격, 순함 = 그 반대, 같음, 그 밖은 비교 불가.
  - twin에 형상이 없으면 `DEFAULT_RE1BF_SHAPE = (0.030, 0.05)`(r67 `EVENTS["RE1bF"]`, 시험이 소스에서 대조)를 씁니다.
  - 기록하는 값: 쌍 수와 A/A 실패 수.
- (3)은 넣지 않았습니다(Q-4 = (A)).

## 2. 시험

### `test_ed8_t8pp.py` (NB-1, 스텁 없음)
- 바꾼 것은 tmp 파일 위치와 GridStore용 tmp 격자 파일뿐입니다.
- 봉인 held-out 키·격자 키와 T-8의 `main.jsonl`은 메인 checkout에서 읽고, 없으면 실패합니다(skip 아님).

| # | 내용 | 결과 |
|---|---|---|
| T-1 | 생산자 꼴 V0 사건 줄 두 개로 `aa_pair_verdict`. 줄 키는 run_one 키와 r5·4368 metrics가 읽는 키 전부이고, `lock_window_alignment`·`t4h_file`·옵션·③ 기록이 없음 | 예외 없음, `j11_state` "입력 없음" |
| T-2 | 봉인 키 job으로 1356줄을 합성해 `stage5` main을 끝까지(CWD는 다른 폴더) | `frozen` 또는 `stop`, not_judgeable 아님, `aa_item_scope` 있음, J11 상태는 모두 "입력 없음" |
| T-3 | V0 줄에 `lock_window_alignment` 있음 | setting_defect, k 동결 없음 |
| T-4 | group이 다름 / V0 아님 / 옵션 있음 | SettingDefect |
| T-5 | 사건 200개로 J7 절단 | NotJudgeable |
| T-6 | VBN 줄에 대체 다리 `n_late` > 0 | census 읽기에서 J11 stop이 실패로 남음 |
| T-7 | VBN 줄에 블록 없음 | J11 판정 불가 유지 |
| T-8 | 저장 main.jsonl(sha 9ad74990)의 같은 (row, group) V0 사건 쌍 | 22쌍 모두 예외 없음, "입력 없음". 값은 단언·출력하지 않음 |

- 같은 파일에 M′-1(census 실패 + 선택 키 불일치 = failed), M′-2, R′-4 시험도 있습니다.

### `test_ed8_t8pp_records.py` (기록 칸)
- J9만 실패한 VBN 단위: 생산자 꼴 줄을 실제 J 항목 경로로 판정 → jx_only.
- J9+J1 → any만. 기준이 실패한 구성원은 제외.
- 사유별 분해(D6, D1_stuck, unknown), 증인 합, 다른 꼴의 기록.
- **판정 불변 고정**: `heldout_jx` 뒤 judged dict가 deepcopy와 같고 상태도 같음. `census_jx` 뒤 outcome이 같고 failed 유지.
- 형상 지배 순서 6경우, 기본 형상, 결정 쌍만 세는지.

### 바꾼 기존 시험
- `test_ed8_judge.py` `stubbed` 고정물: 이제 `aa_pair_verdict`를 스텁합니다(층·순서 논리 전용). 실제 경로는 T-1~T-8이 덮습니다.
- `test_ed8_gate_judge.py`: M′-2에 맞춰 위 두 시험으로 바꿨습니다.

## 3. 검증
| 검증 | 결과 |
|---|---|
| ed8 시험 6파일 | 216 통과 |
| ruff·codespell(바꾼 파일) | 0 |
| 전체 시험 T8″ `5955f25b` | 2 실패(기존), 8895 통과, 134 건너뜀, 1498 s, 끝 시점 HEAD T8″·clean |

- 전체 시험 조건: ed8-judge2에서 Chrono-dev `-n 12 --dist loadfile`, `OUTRIGGER_RECORDS_ROOT=main`, `NUMBA_CACHE_DIR`은 scratchpad였습니다. 시작 전 `reserve.py list`로 확인한 유효 예약은 0이었습니다.
- junit 대조(상태 변화 목록을 파일로 남김)
  - `junit_compare_T8p_vs_T8pp.txt`: 상태 변화 0, 새 시험 33(미통과 0), 없어진 시험 1(바뀐 P8-15 시험).
  - `junit_compare_C8_vs_T8pp.txt`: 상태 변화 0, 새 시험 291(미통과 0), 없어진 시험 1. 이 1개는 `test_ed7_adoption::test_both_candidates_qualifying_is_not_decided`이며, T8에서 판 7 시험 파일을 60ebb4a4 판으로 들여올 때 바뀐 것입니다.
- **중간 커밋 c877b8cd의 전체 시험(기록 칸 추가 전, 대체됨)**
  - 결과: 2 실패, 8879 통과, 134 건너뜀, **오류 2**(`test_k2_chrono_runner` 2개, `No module named 'l1r_variant'`).
  - 대조 파일: `junit_compare_T8p_vs_c877b8cd_superseded.txt`.
  - 그 파일을 단독으로 돌리면 30개 모두 통과했고, 최종 커밋 전체 시험에서도 통과했습니다.
  - 원인 추정: 시험 쪽 `_import`가 `02_chrono` 경로를 import 직후 빼서, 같은 xdist 작업자의 다른 파일이 그 경로를 남겨 두었는지에 따라 결과가 달라집니다(파일 배분 순서 의존, 기존 시험의 성질).
- 증거: 새 폴더 `ed8_design\t8pp_evidence\`(SUMS `3f170c9d…`)
  - `junit_T8pp_5955f25b.xml`, `suite_T8pp_5955f25b.log`
  - 대체된 c877b8cd의 junit·log
  - 대조 txt 3개
- 정리: ed8-judge2의 `__pycache__` 13개와 `.hypothesis`를 지웠습니다(status --ignored 비어 있음). scratchpad `python-ed8-t8pp`도 지웠습니다.

## 확인 필요
1. **`jx_only_units`의 C-D·C-G 처리.** census의 C-D·C-G 단위는 J 항목이 아니라 V0 비교로 실패합니다. 그래서 그 실패 이름을 `V0-comparison fail`로 두어 jx_only·jx_any에 들어가지 않게 했습니다. stats Q-2 정의("실패 항목 합집합")를 C-G 칸에 그대로 적용한 해석입니다.
2. **`j11_opportunity_by_reason` 사유 토큰 읽기.** 이벤트 `INFO_ROD_PRESSURE_FAULT_REASON:<leg>:<reason>`에서 reason의 첫 단어가 D1·D1_stuck·D2·D3·D4·D6이 아니면 unknown으로 셉니다. 실제 사유 문자열의 꼴은 생산자 줄로 확인하지 못했습니다(합성 시험만 했음).

## 메인 세션 권고
- T8″ 재감사(verif-protocol-auditor) 뒤 `ed8-judge2`를 잠가 주십시오.
- 감사 M-5 키 존재 점검에 다음 두 가지를 더하기를 권합니다.
  - 5단계 V0 줄에서 `lock_window_alignment` 없음(N-A 전제).
  - VBN 줄 `events`에 `INFO_ROD_PRESSURE_FAULT_REASON`의 사유 꼴, `probe_d6_record.not_opened_rounds`·`would_warn`(값 출력 없음).
- control 결정문 6.1이 권한 C8 V0 한 줄 스모크(실제 생산자로 태그·`hydraulics_record` None·블록 없음을 확인하는 것)는 하지 않았습니다(실행 금지 범위).

## 공개 (실제 행위)
- 블라인드 경로는 열지 않았습니다.
- Grep·Glob·Read 범위: 하위 경로나 단일 파일만 지정했습니다.
  - 파일: `ed8-judge2\04_scripts\04_hydraulic\coupled\*`, `05_tests\unit\*`, `03_src\outrigger_sim\control\two_pressure.py`, `06_analysis\03_hydraulic\coupled\v5\paper_runs\scripts\judge_stage1_r5.py`, `04_scripts\03_control\s8\r67_g1_screen.py`, 결정문·stats 문서.
  - Glob: `04_scripts` 아래 `**/l1r_variant.py`·`**/r67_g1_screen.py`, `…\paper_runs\scripts` 아래 `judge_stage1_r5.py`.
- 저장 `main.jsonl` V0 줄은 T-8 시험이 읽었습니다(sha 고정, 값은 출력하지 않음).
- **훅 차단 1회:** PowerShell here-string 안의 Python `del` 문을 훅이 `Remove-Item`으로 보고 명령 전체를 막았습니다. 실행된 것은 없고, 같은 내용을 Write로 새 시험 파일에 썼습니다.
- Bash는 쓰지 않았고 파이프도 없습니다. 프로세스는 종료하지 않았습니다.

사용한 스킬: 없음
