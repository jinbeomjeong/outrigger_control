# 판 8 T8′ 해석 결정문: B-3·M-4·M-1·R-2 (control-expert, 2026-11-26)

- **상태**: 해석 결정이다. 봉인 명세 S8-R `jp3_remedy_spec_v8_rules.md`(sha256 `35f9eba8f98f93dd…2c121520`, 이번 작업 중에 다시 계산해 일치를 확인함)는 고치지 않았다. 아래 결정은 판정서와 T8′(python-expert) 구현에 쓴다.
- **근거**
  - 실행 전 감사 `audit_prerun/verif_c8_t8.md`의 B-3·M-1·M-4·R-2, 확인 필요 2·3
  - `impl_report_ed8/t8_report.md`(확인 필요 3·4), `c8_t8_report.md`
  - 사용자 결정(2026-11-26)
    - B-1은 (가)로 한다.
    - 5단계 aa2·aa3는 조건 없이 모두 돈다.
- **코드 기준**: T8 worktree `ed8-judge`(ecf6c142)와 C8 worktree `ed8-impl`(56849248)의 파일. 읽기만 했고, 두 worktree의 `status --porcelain --ignored`는 작업 뒤에도 비어 있다.

## 요청 밖 추가(먼저 밝힘)
네 질문에 답하다가 아래 다섯 가지를 더 정했다. 모두 판정 정의를 바꾸지 않는다. 입력 완결성·키 해석·정체성 범위를 좁히는 구현 요구다.

| # | 내용 | 이유 |
|---|---|---|
| A-1 | 5단계 판정은 출력 파일 셋(v0 678·aa2 339·aa3 339)을 모두 요구한다. 줄 집합이 정확히 맞아야 한다(빠짐·중복·여분이 있으면 not_judgeable) | 지금 `judge_stage5`는 `rows_by = {job_key: row}`(jp3_ed8_judge.py:731)라서 중복을 말없이 덮어쓰고 여분을 무시한다. 사용자 결정에 따라 aa2·aa3는 항상 존재한다 |
| A-2 | **발견 F-1(도구 결함 후보)**: `four-case`가 사례 키를 12b 입력 통계와 다른 함수로 해석한다 | 아래 2.4. 그대로 두면 "4사례가 12b 틀에 없다"는 잘못된 기록이 나올 수 있다 |
| A-3 | V0 정체성 기대값은 **5단계에서 새로 돈 V0 줄에만** 적용한다. 저장 V0(main.jsonl)에는 적용하지 않는다 | 저장 main.jsonl V0 100줄은 모두 `controller_tag`가 없다(실측). 저장 V0는 sha 고정(9ad74990)으로 정체성을 대신한다 |
| A-4 | R-2 권고에 r79 줄의 `hydraulic_options.ed8_settings` 스위치 비교를 더한다 | 지금 r79 줄은 `whole_options=False`라서 `p1_patch`만 비교한다(jp3_ed7_judge.py:407-411) |
| A-5 | `identity_defects`는 줄 하나의 정체성 함수가 예외를 내면 그 줄의 정체성 문제로 바꾼다(전체 종료 3 금지) | B-3과 같은 유형(설정 options가 None)이 다른 설정에서 다시 나오는 것을 막는다. M-2와 같은 방향이다 |

## 0. 요약
| # | 질문 | 결정(요지) | 구분 | 실패 시 상태 |
|---|---|---|---|---|
| 1 | B-3: 5단계 V0 줄 정체성 | V0 전용 기대값을 둔다. 확인 항목: `job.setting` = `V0`, `controller_tag` = `final_C4G2_LAS_K1`, `hydraulic_options`·`hydraulics_record` = null(③ 기록 없음), 판 6·7·8 기록 키 9개 없음, `head_only_declared` ≠ true. 하나라도 어긋나면 setting_defect | 판정(정체성, 10절) | setting_defect |
| 2 | M-4: 12b 8절 "4사례를 뺀 사례 수·P-pred 입력 통계" | P-pred **입력**(`jp3_12b_ppred.InputStatistics`·`decision_record`의 입력 필드)을 전체·4사례 제외·4사례 셋으로 기록한다. `k_allow`는 다시 계산하지 않는다. 사례 수 = 틀 167 − 틀 안 4사례 | 기록(8절·10절) | 입력 결함 = setting_defect(12b 판정 상태는 바꾸지 않음) |
| 3 | M-1: census 선택 사용 키 파일 | python-expert가 T8′에서 결정적 생성기와 파일을 만든다. 세 raw의 sha를 고정한다. 대응은 팔 접두를 떼고 VBM→VBN, VBMslow→VBNslow, LSM4→LSN4다. **설정까지 맞춰** 대조한다. 기대는 23 job, 단위 18(C-J 11, C-S 1, C-D 0, C-G 6)이다. 0건이거나 기대와 다르면 setting_defect | 기록(5.2·13절 13). 입력 결함은 10절 목록 밖이라 setting_defect | setting_defect |
| 4 | R-2 | **T8′에 넣기를 권한다.** run_v5 판 8 줄은 최상위 `ed8_settings` 수치를 명세 값과 비교한다. r79 줄은 스위치만 비교한다(A-4) | 판정(정체성) | setting_defect |

---

## 1. B-3: 5단계 V0 줄의 정체성 기대값

### 1.1 명세 근거(봉인 문면)
- 3.6 표 끝 줄(spec:158) "기존 설정 전부 | 그대로 | 그대로 | 비트 동일(P8-0)": V0은 기존 설정이고, 제어기는 v5 기본 그대로다.
- 3.6 정체성(spec:163): "어긋나면 `setting_defect`". 10절 표(spec:343)는 정체성을 판정 항목으로 둔다.
- 4절 5단계(spec:202) "C8(V0만)"과 spec:210 "5단계는 V0만. G′ VBN은 8단계 전에 돌지 않는다".
- 7.1(spec:282) "설정 VBN, 기준 V0". 7.3(spec:291)·7.4(spec:303)는 V0 단위·A/A 짝이다.
- 판 8의 정체성 목록(태그 `_ED8`, `lsb_components`, `probe_d6_settings`, ③ rev 7 등)은 VBN 계열 설정의 것이다. V0에 이 기대를 걸면 판 7 함수가 예외를 내는 것이 B-3이다(jp3_ed7_judge.py:316-323 `setting V0 has no hydraulic options`).

### 1.2 코드 사실(생산자 경로, 파일:줄)
| 사실 | 위치 |
|---|---|
| `"V0": (False, {})`이므로 `options_of("V0")` → `(flow, None)` | run_v5.py:123, 887-909 |
| 5단계 배치: `ed8_heldout_v0` = 슬롯마다 `v0_pair.job` + `aa_order[0]`(678), `ed8_heldout_aa2/3` = `aa_order[1]`/`[2]`(각 339) | run_v5.py:458-463, 490-513 |
| 러너는 `run_v5.py <batch> --jobs-file heldout_g_ed8.json` | ed8-impl `prelaunch_j9/run_steps_ed8/step5_heldout_v0_ed8.ps1`:19-25 |
| 줄의 `hydraulic_options`·`hydraulics_record`는 항상 키로 쓰인다(값은 result에 없으면 None) | run_v5.py:959-960 |
| options가 None이면 `plant_options_record`는 `{"controller_tag": controller_tag(None, config)}`만 돌려준다. ③ 기록(`hydraulics_record.extend_bound_check`)은 없다 | verdict_runs.py:873-877 |
| `config` = 그 실행 제어기의 config(`_finish`가 설정) | verdict_runs.py:217, 874 |
| `lsb_*`는 `lock_start_b.is_enabled`일 때만, `probe_d6_*`는 `probe_d6.is_enabled`일 때만, `probe_stiffness_record`·`ib_block_record`·`ed8_settings`·`ed8_record`는 판 8 제어기이거나 프로세스 스위치가 켜졌을 때만 붙는다 | verdict_runs.py:291-302, 311-320, 350-354, 374-392 |
| 프로세스 스위치 `enable_ed8_record()`를 부르는 곳은 `ed8_probe.py`:275뿐이다(run_v5에는 없음) | coupled `*.py` Grep |
| V0은 `T4H_SETTINGS`에 없으므로 T4h와 `t4h_file`이 없다 | run_v5.py:761-762, 797 |

- 실측(`v0_identity_probe.py`, dynamics-dev, ed8-judge 코드 import, 실행 없음)
  - `controller_tag(None, C2Config().with_10hz_d1())` = `final_C4G2_LAS_K1`
  - 그 프리셋의 스위치: `has_ed8_changes` 거짓, `lock_start_b` 꺼짐(components []), `probe_d6` 꺼짐, LAS-b 켬, K1 순서 관문 켬
  - `options_of("V0")[1]` = None, `"V0" in T4H_SETTINGS` = 거짓
  - 저장 main.jsonl V0 100줄: `controller_tag` 없음 100/100, `hydraulic_options` null 100, `hydraulics_record` null 100, 판 6~8 기록 키 0

### 1.3 결정: V0 줄 기대값(5단계 출력 1356줄 각각)
| 필드 | 기대 | 어긋나면 |
|---|---|---|
| `job.setting` | `"V0"` | 정체성 문제(spec:202·210 위반: 5단계에 V0 아닌 줄) |
| `controller_tag` | `== "final_C4G2_LAS_K1"`(상수 `V0_CONTROLLER_TAG`). 키가 없어도 문제다 | 정체성 문제 |
| `hydraulic_options` | None(키는 있고 값 null; 없어도 허용) | 정체성 문제 |
| `hydraulics_record` | None. 따라서 `extend_bound_check` 없음(③ 기록 없음) | 정체성 문제 |
| `head_only_declared` | true가 아님(false 또는 없음) | 정체성 문제 |
| 없어야 하는 키 `V0_ABSENT_KEYS` | `lsb_components`, `lsb_settings`, `lsb_record`, `probe_d6_settings`, `probe_d6_record`, `probe_stiffness_record`, `ib_block_record`, `ed8_settings`, `ed8_record`. 없거나 None이어야 한다 | 정체성 문제(판 6·7·8 제어기 또는 기록 스위치가 섞였다는 신호) |
| 검사하지 않음 | `t4h_file`, `resume_k1`, `review_record`, `harness_class`(정체성 아님) | – |

- **오류 줄**(`"error"` 키)에는 정체성을 적용하지 않는다. 그 슬롯은 지금처럼 not_judgeable이다(jp3_ed8_judge.py:692-704).
- **적용 범위(A-3)**: `judge_stage5`가 읽는 `--v0-rows` 세 파일의 줄에만 적용한다.
  - census 저장 V0(main.jsonl)와 저장 격자 run에는 적용하지 않는다. 이들은 sha 고정 입력이다.
  - `judge_heldout`(8단계)은 지금처럼 VBN 줄에만 정체성을 본다. 5단계 V0 줄은 5단계 판정에서 이미 확인됐고, `ho_k_selection.json` sha로 고정된다.

### 1.4 구현 명세(python-expert, `jp3_ed8_judge.py`)
1. 상수
   - `V0_SETTING = "V0"`
   - `V0_CONTROLLER_TAG = "final_C4G2_LAS_K1"`
   - `V0_ABSENT_KEYS = (...)`(위 9개)
2. `def v0_identity_problems(row: Mapping) -> list[str]`: 1.3 표를 그대로 구현한다.
3. `identity_defects(rows)`
   - 줄마다 `row["job"]["setting"] == "V0"`이면 `v0_identity_problems`를 쓴다.
   - 그 밖의 줄은 `ed8_identity()` 안에서 판 7 `ed7_identity_problems(row, ed7.setting_identity(setting))`를 쓴다.
   - (A-5) 판 7 쪽이 `ed7.SettingDefect`·`ed7.NotJudgeable`·`KeyError`를 내면 전체를 예외로 끝내지 말고, 그 줄의 문제 `[f"identity not computable: {exc}"]`로 기록한다. 이것은 정체성 문제이므로 setting_defect가 된다.
4. `judge_stage5`
   - **입력 완결성(A-1)**: `--v0-rows`/`--step-done`은 정확히 3쌍이다(배치 `ed8_heldout_v0`·`ed8_heldout_aa2`·`ed8_heldout_aa3`).
     - 파일마다 기대 job 집합 = `run_v5.heldout_v0_jobs(<keys>, <batch>)`이다. 대조는 `match_rows`와 같은 규칙(job_key 1:1)으로 한다.
     - 파일 수 ≠ 3, 빠짐, 중복, 여분이 있으면 `not_judgeable` 근거에 넣는다.
     - 기대 수: v0 678, aa2 339, aa3 339, 합 1356. 실측으로 키 파일에서 1356 job이 모두 서로 다르고 설정은 모두 V0다. `aa_order` 길이는 3이 171슬롯, 15가 48슬롯, 7이 120슬롯이고, 모두 3 이상이다.
   - **순서**(10절 상태 순서와 "계산되지 않은 항목 = 판정 불가")
     - (a) 키·격자 sha와 단계 기록을 확인한다(지금과 같음).
     - (b) 오류가 아닌 모든 줄에 `identity_defects`를 돌려 `setting_defects`에 넣는다.
     - (c) 완결성 문제를 `not_judgeable`에 넣는다.
     - (d) (b)·(c)가 모두 비었을 때만 `slot_inputs`와 `rules.stage5_selection`을 계산한다.
     - 최종 상태
       - (b)가 있으면 `setting_defect`, 없고 (c)가 있으면 `not_judgeable`이다. 이때 `stage5_selection` 결과는 내지 않는다(`frozen`이 나올 수 없음).
       - (b)·(c)가 없으면 `stage5_selection`의 `frozen`/`stop`/(규칙의) `not_judgeable`이다.
     - 지금 코드(선택 계산 뒤 `stop`이 아니면 덮어씀, 741-743행)를 바꾸는 것이다. 정체성 결함이 있으면 그 데이터로 $k$를 동결하지 않는다.
   - report: `identity_defects`(줄별 job과 문제), `status_basis`(세 목록), `inputs.v0_rows`(파일 셋의 단계 기록).
5. M-2(감사)와 함께 `main`에서 `ed7.SettingDefect` → setting_defect, `ed7.NotJudgeable` → not_judgeable로 바꾼다.

### 1.5 시험(T8′, 스텁 없이)
- **생산자 꼴 V0 줄**: `run_one` 반환 꼴을 따른 합성 줄로 `v0_identity_problems`가 `[]`이다.
  - 필드: `job`(setting V0), `controller_tag` `final_C4G2_LAS_K1`, `hydraulic_options` None, `hydraulics_record` None, `head_only_declared` False, `resume_k1`, `review_record`, `commands_sha256`
  - 같은 줄로 `judge_stage5`를 끝까지 돌린다. 감사 B-3대로 `identity_defects`를 스텁하지 않는다. 감사 M-5대로 T4h 없는 V0 줄이 `t4h_folders_of`·`metric_of` 경로를 통과하는지도 이 시험에서 확인한다.
- **어긋남마다 문제가 나는지**
  - 태그 `final_C4G2_LAS_K1_LSB_ED8`, 태그 없음
  - `hydraulic_options` dict, `extend_bound_check` 있음
  - `V0_ABSENT_KEYS` 9개 각각 있음
  - `head_only_declared` true
  - `job.setting` `VBN`
- **상수 묶음**
  - `v5_options.controller_tag(None, C2Config().with_10hz_d1()) == V0_CONTROLLER_TAG`
  - `run_v5.options_of("V0")[1] is None`
  - `verdict_runs.plant_options_record(None, config=C2Config().with_10hz_d1()) == {"controller_tag": V0_CONTROLLER_TAG}`(생산자 함수, 실행 없음)
- **완결성**: 파일 2개, 빠짐 1, 중복 1, 여분 1 → not_judgeable. 정체성 문제와 완결성 문제가 함께 있으면 setting_defect.
- **A-5**: options가 None인 다른 설정 이름의 줄 → setting_defect(종료 2). 종료 3이 아니다.
- **A-3**: census 경로에서 저장 V0 줄이 `identity_defects`에 들어가지 않는다(회귀).

---

## 2. M-4: 12b 8절 "4사례를 뺀 사례 수·P-pred 입력 통계"

### 2.1 명세 근거
- spec:325 "12b: 판 7 6.4 그대로(… 입력 바닥 VBKN0 b1·b2)".
- spec:327 "12b 판정은 그대로 두고, 기록으로 '4사례를 뺀 사례 수·P-pred 입력 통계'와 '4사례의 VBKN0 교착 서명'을 따로 낸다. 이 4사례의 통과는 L-2 효과의 증거가 아니다." 같은 문장에 "P-pred 입력의 미도달이 줄면 판정이 엄해지는 쪽"이라는 해석도 있다.
- 10절(spec:344) "12b 4사례 기록"은 기록이다. 10절(spec:345)의 기록 실패 닫힌 목록 (3)은 "교착 서명 계산 실패"이고, 목록 밖 문제는 입력 결함이다.

### 2.2 "P-pred 입력"의 코드 정의
- `jp3_12b_ppred.input_statistics`(jp3_12b_ppred.py:156-181)
  - VBKN0 b1·b2 줄을 `judge.classify_line`으로 나눈다.
  - `no_trigger`·`pre_trigger_fallback`은 뺀다(`left_out`). `unlatched`는 `InputStop`이다.
  - 사례 $i$마다 남긴 줄 수 $n_i$와 미도달 수 $k_i$를 센다.
- 칸(셀) $c$의 통계: $K_c=\sum k_i$, $N_c=\sum n_i$. 두 줄 모두 남고 모두 READY인 사례 수는 $n_{both}$, 그 가운데 READY 차 > 30 s인 수는 $a_{30}$이다.
- b4를 쓰면 `b4_input`(184-195)이 $K_{TRw}$, $N_{TRw}$, 기회 수를 낸다.
- 기록 꼴은 `decision_record`(287-303)다. 그 가운데 **입력**은 `K_c`, `N_c`, `a30`, `n_both`, `cases{k,n}`, `left_out_lines`, `replay_lines`, `b4{…}`이다. **출력**은 `k_allow`, `p_n23_gt_k`, `p_n23_gt_k_minus_1`, seed, 추출 수다.
- 12b `decide`는 이 기록을 `p_pred`로 남긴다(jp3_12b_judge_ed7.py:145-148).

| 기호 | 뜻 | 단위 |
|---|---|---|
| $n_i$ | 사례 $i$의 남긴 VBKN0 줄 수(b1·b2, 0~2) | 줄 |
| $k_i$ | 그중 READY 미도달 줄 수 | 줄 |
| $K_c$, $N_c$ | 칸 $c\in\{\tau_C,\tau_R\}$의 $\sum k_i$, $\sum n_i$ | 줄 |
| $a_{30}$, $n_{both}$ | 두 줄 모두 도달한 사례 중 READY 차 > 30 s 수 / 그런 사례 수 | 사례 |
| replay_lines | 재생 대상 기회 줄 수 $\sum_i (n_i-k_i)$(+ b4 기회 수) | 줄 |

### 2.3 결정(정의)
- **4사례**: P8-14 계획(`raw/plans/P814-B-VBKM0.json`, sha256 `99e50653…`)의 `faults` 키 4개를 **`jp3_12b_judge.case_of`**로 바꾼 사례 이름 집합이다. 이 함수는 `cand=…#` 접두와 seed 토큰을 뗀다(jp3_12b_judge.py:254-260). 서로 다른 사례가 정확히 4개여야 한다.
- **12b 사례 틀**: 12b `decide`가 읽은 `selection.json`의 `cell_table` 사례 집합이다. 크기는 `judge.CASES_PER_BLOCK` = 167이어야 한다(jp3_12b_judge.py:136; jp3_12b_plan.py:126이 먼저 막으므로 방어용 점검이다).
- **"4사례를 뺀 사례 수"** = 틀 크기 167 − (4사례 ∩ 틀)의 크기다. 모두 들면 163이다. 함께 기록할 것:
  - 남긴 줄이 하나라도 있는 사례 수(전체·제외 후)
  - 기존 `vbkn0_lines`·`vbkn0_lines_without_four_cases`
- **"P-pred 입력 통계"**
  - `input_statistics`를 같은 VBKN0 b1·b2 줄에 대해 두 번 계산한다: **all**(그대로)과 **without_four**(틀과 줄에서 4사례를 뺌).
  - 결과마다 2.2의 입력 필드(`K_c`, `N_c`, `a30`, `n_both`, `left_out_lines`, `replay_lines`, 사례 수)를 기록한다.
  - `decide`의 `blocks_used`에 b4가 있으면 b4 입력(`K_TRw`, `N_TRw`, `opportunities`, `left_out_lines`)도 all·without_four로 기록한다. b4가 없으면 `"b4": "not used"`로 적는다.
  - **four**: 4사례 각각의 칸, $k_i$, $n_i$, 블록별 줄 분류(`classify_line` 범주)를 기록한다.
- **`k_allow`는 다시 계산하지 않는다.** 명세 문면은 입력 통계이고, 4사례를 뺀 `k_allow`는 대체 판정값으로 읽힐 수 있다. 방향은 $K_c$·$N_c$ 차이로 충분히 보인다(spec:327의 해석).
- **일관성 점검**: all은 `decide` 기록의 `p_pred` 입력 필드와 같아야 한다(`cases`의 `{k,n}`, `K_c`, `N_c`, `a30`, `n_both`, `left_out_lines`, `replay_lines`, b4). 다르면 이 기록이 판정에 쓰인 입력의 것이 아니므로 setting_defect다.
- **교착 서명**: 4사례의 VBKN0 줄 전부(b1·b2, b4를 썼으면 b4)에 판 7 6.2 서명을 낸다(지금 `stall_signature`). None은 기록 실패 (3)이고 상태를 바꾸지 않는다. `record_failures`에 넣는다.

### 2.4 발견 F-1(A-2): `four-case` 사례 키 해석 불일치
- `plan_cases`는 `key.removeprefix("cand=current#")` 뒤에 `case_of_key`를 쓴다. `four_case_record`는 줄 키에 접두를 떼지 않고 `case_of_key(line.get("key"))`를 쓴다(jp3_12b_judge_ed8.py:75-84, 106-109).
- `case_of_key`는 `|`로 나눈 둘째 토큰만 지우므로, 접두가 있는 키는 `cand=current#L2|g6|…`가 되어 계획 사례 `L2|g6|…`와 맞지 않는다.
- 실측(`r79_key_form.py`): P8-14 raw의 r79 줄 키 13/13과 계획 `faults` 4/4에 모두 `cand=current#` 접두가 있다. 둘째 토큰은 `s<숫자>`다.
- 12b의 판 7 판정 경로는 `plain_key`·`case_of`로 접두를 뗀다(jp3_12b_judge.py:311, 258-260; jp3_12b_ppred.py:178).
- 12b VBKN0 줄 키가 같은 r79 도구의 꼴이면 `cases_in_12b_frame` = [], `four_case_vbkn0_lines` = []가 나온다. 즉 "4사례가 12b 틀에 없다"는 잘못된 기록이 된다.
- **결정**: 계획 키와 줄 키 모두 `judge.case_of`, 줄 키 비교는 `judge.plain_key`로 통일한다. 입력 통계와 같은 함수다. 접두가 있는 키로 시험한다.

### 2.5 구현 명세(`jp3_12b_judge_ed8.py four-case`)
- **새 인자**
  - `--selection <selection.json>`·`--selection-sha256 <sha>`: decide가 읽은 파일이어야 한다. `decide` 기록의 `ed7_record.inputs_sha256.selection`과 같아야 하고, 아니면 setting_defect다.
  - `--decision <decide record>`: `status` ∈ {`decided`}, `blocks_used`·`p_pred`를 읽는다.
  - `--vbk0 b<j>=…`: sha가 `ed7_record.inputs_sha256.vbkm0_files`와 같아야 한다.
- **줄 읽기**: `judge.load_lines`와 같은 꼴로 읽는다(키는 `plain_key`, `Line(key, row, t4h_dir / t4h_file)`). 범주는 `ppred._line_category`를 쓴다.
- **계산**: `ppred.input_statistics(selection_minus, blocks_minus)`
  - `selection_minus = {**selection, "cell_table": [row for row in selection["cell_table"] if row["case"] not in four]}`
  - `blocks_minus = {b: {k: l for k, l in lines.items() if judge.case_of(k) not in four}}`
- **출력 키**: `four_cases`, `frame{n_cases, cases_in_frame, cases_not_in_frame}`, `n_cases_without_four`, `p_pred_inputs{all, without_four, four}`, `all_equals_decision`(bool), `blocks_used`, `four_case_vbkn0_lines[{block, key, case, category, error, stall_signature}]`, `vbkn0_lines`, `vbkn0_lines_without_four_cases`, `record_failures`, `rule`(k_allow를 다시 계산하지 않는다는 문장 포함)
- **상태**(이 기록 도구의 것. 12b `decide`/`judge` 상태는 바꾸지 않는다)

| 조건 | 상태 | 비고 |
|---|---|---|
| 계획 sha, 단계 기록, selection·decision·블록 sha 불일치 | setting_defect | 지금과 같은 규칙 |
| 서로 다른 4사례 ≠ 4, `cases_not_in_frame` ≠ ∅, 틀 ≠ 167 | setting_defect | 10절 목록 밖(spec:327 "든다"의 전제가 깨짐) |
| all ≠ decide `p_pred` 입력 | setting_defect | |
| `InputStop`(unlatched) | setting_defect | decide도 같은 이유로 멈춘다 |
| decide 기록·블록 파일 없음 | not_judgeable | |
| `stall_signature` None | written(+ `record_failures`) | 기록 실패 (3) |
| 그 밖 | written | |

- setting_defect가 나면 메인은 판정서 12b 절에 "8절 기록 입력 결함"을 적고 사용자에게 묻는다(4절 멈춤). 12b 판정 문면은 그대로다.
- **권고(선택)**: `four-case --frame-only`(selection만 읽어 4사례가 틀 안에 있는지 확인)를 12b 계획 단계 직후에 돌리면, spec:327의 "(확인: 판 8 12b 계획 키로, 12b 계획 단계에서)"를 VBKN0 실행 전에 볼 수 있다.

### 2.6 시험
- 접두가 있는 계획 키와 줄 키(`cand=current#L2|s50|…`)로 `cases_in_frame`이 4다(F-1 회귀).
- 합성 VBKN0 b1·b2(사례 6개, 4사례 포함, 범주 섞음): all과 without_four의 `K_c`·`N_c`·`a30`·`n_both`·`replay_lines`를 손계산 값과 비교한다.
- all과 decide `p_pred`가 다르면 setting_defect다.
- b4를 썼을 때와 안 썼을 때.
- 틀 밖 사례 → setting_defect.
- `stall_signature` None → written + `record_failures`.
- 출력에 `k_allow` 키가 없다.

---

## 3. M-1: census 선택 사용 키 파일

### 3.1 명세 근거
- 5.2 끝(spec:238): "'선택 사용 키 / 그 밖' 두 칸의 기회·실패 수(기록). 선택 사용 키 = P8-9·P8-9′·P8-14에서 돌린 키 가운데 census 단위인 것(13절 13)".
- 5.3(spec:245): "P8-9 20키, P8-14 VBM 23키 중 census 단위 — R2 e0.001, S4 e0.002, S8 e0 포함". 5.1(spec:218-221)의 설정 대응은 VBM → VBN, LSM<n> → LSN<n>, VBM<key> → VBN<key>다.
- 10절(spec:345): 기록 실패는 닫힌 목록이고, 목록 밖 문제는 입력 결함(setting_defect)이다.
- 원천 sha(머리말)
  - P8-9 `control_early_handover/probe_8a2a52ce/raw/runs.jsonl` `3c0979f57000dd2236908d0e08df4fa6776e16a7d58458701ccae10345fd6aeb`(spec:33)
  - P8-9′ `…/h3p/raw/runs.jsonl` `06b9d8fcb40f44d054f7fbfda922f5032c096c9750974183457d0fa7064b95e5`(spec:34)
  - P8-14 `control_level_deadlock/probe_8a2a52ce/raw/runs.jsonl` `89efe66fc521f6d58c8c90304a9258747eef45d422ef43666a53f5ddd7fa9418`(spec:40)
  - 세 값을 다시 계산했고 모두 일치한다.

### 3.2 원천 구조(실측, job 키만 봄; `key_structure.py`·`key_list.py`, 판정 값은 출력하지 않음)
| 원천 | 줄 | job 있는 줄 | job 필드 | job `setting` 꼴(팔 접두 - 플랜트) | 서로 다른 job(설정 대응 뒤) |
|---|---|---|---|---|---|
| P8-9 | 60 | 60 | case, eps, offset_s(57), twin(39), setting, mask, t4h_dir | `P89-{A,H1,H3}-{VBM 18, LSM4 1, VBMslow 1}` | 20 |
| P8-9′ | 7 | 7 | 같음(twin 2) | `P89-H3p-VBM` | 7 |
| P8-14 | 82 | 69(r79 13줄은 `job` 없음, `key` 꼴) | case, eps, offset_s(57), twin(39), setting | `P814-{B,L1,L2}-{VBM 21, LSM4 1, VBMslow 1}` | 23 |
| 합집합 | | | | | **23**(P8-9·P8-9′는 P8-14의 부분집합) |

- census 키(`keys_seal_41e107e9/census_keys_ed8.json`, sha `278b332f…`): 줄 필드는 `stage`·`job`·`role`·`source_setting`·`v0_pair`다. 단위 467 = C-J VBN 100 + C-S 판정 4설정 184 + C-D VBN 12 + C-G 171.
- **설정까지 맞춘 대조**(플랜트 대응 VBM→VBN, VBMslow→VBNslow, LSM4→LSN4, job 나머지 필드 완전 일치)

| 구분 | 수 | 내용 |
|---|---|---|
| census 단위 | **18** | C-J VBN 11(R15 o0·o0.05, R16 o0·o0.025·o0.05·o0.075, R2 e0.001, S4 e0.002, S7 e0.002, S8 e0, R12 top FR Fs8 o0), C-S VBNslow 1(R12 top FL Fs0 o0, `judged_vs_V0`), C-G 6(R12 RE1bF bottom FL Fs4 o0·FR Fs0 o0·FL Fs2 o0.025·FR Fs2 o0.075·FR Fs4 o0.075, FS24 bottom FR Fs8 o0), C-D 0 |
| census 줄이지만 단위 아님 | 1 | LSN4 R12 top FR Fs0 o0.05(C-J `judged_vs_VBN`, (ii) 비교 줄) |
| census에 없음 | 4 | R12 RE1bF bottom FL Fs2 o0, FR Fs2 o0, FR Fs4 o0, top FL Fs8 level o0 |

- 설정을 무시하고 대조하면(지금 도구의 방식, jp3_ed8_judge.py:552-563) C-J 13·C-S 36·C-G 6 = 55단위가 된다. C-S의 35개는 프로브에서 돌지 않은 플랜트(VBNfast·c005·c04 등)다. 감사 M-1의 우려가 맞다.

### 3.3 결정
1. **만드는 주체**: python-expert(T8′). 판정 도구 폴더에 결정적 생성기 `04_scripts/04_hydraulic/coupled/ed8_selection_keys.py`를 둔다(T8′ diff, P8-11 범위 안). 파일은 메인 checkout에 생성기로 만든다. 메인은 그 파일과 SUMS를 커밋한다(6단계 census 전, T8′ 재감사 전).
2. **원천과 고정**
   - 위 세 raw, sha는 생성기 상수 `SOURCE_SHA256`이다. 다르면 거부(종료 2)한다.
   - census 키 sha `278b332f…`도 생성기가 확인한다.
3. **읽기 규칙**
   - `job` dict가 있는 줄만 쓴다. r79 줄(`job` 없음)은 건너뛰고 원천별 수를 기록한다(기대: P8-9 0, P8-9′ 0, P8-14 13). census에는 r79 줄이 없다.
   - 플랜트 = `setting.rsplit("-", 1)[1]`, 팔 = 앞부분.
   - `PLANT_TO_CENSUS = {"VBM": "VBN", "VBMslow": "VBNslow", "LSM4": "LSN4"}`. 표에 없는 플랜트는 거부한다.
   - job 꼴 = 원 job에서 `setting`·`mask`·`t4h_dir`을 빼고 `setting`을 census 설정으로 바꾼 run_v5 job이다. `run_v5.job_key`로 중복을 없애고, 그 키 오름차순으로 정렬한다.
4. **파일**: `06_analysis/02_control/j_p3_cause/ed8_design/keys_selection_ed8/selection_keys_ed8.json`. 이미 있으면 거부한다. 쓰기 꼴은 UTF-8, LF, `sort_keys`, indent 1이다. 같은 폴더에 `SHA256SUMS`를 둔다.
   ```
   {"rule": "jp3_remedy_spec_v8_rules.md 5.2, 5.3, 13 13 (selection-used keys, record)",
    "sources": {"P8-9": {"path": <repo 상대>, "sha256": ...}, "P8-9p": {...}, "P8-14": {...}},
    "census_keys_sha256": "278b332f...", "plant_to_census": {...},
    "r79_lines_skipped": {"P8-9": 0, "P8-9p": 0, "P8-14": 13},
    "jobs": [<run_v5 job, setting = census 설정> x 23],
    "entries": [{"job_key", "sources", "probe_arms", "census_role": "unit:<stage>" | "line:C-J judged_vs_VBN" | "absent"}],
    "expected": {"jobs": 23, "unit_matches": 18, "by_stage": {"C-J": 11, "C-S": 1, "C-D": 0, "C-G": 6},
                 "non_unit_census_lines": 1, "absent_from_census": 4}}
   ```
5. **census 대조**(`jp3_ed8_judge.selection_unit_ids` 고침)
   - wanted = {(`job["setting"]`, `plain_job_key(job)`)}
   - 단위 일치 조건: (`unit["setting"]`, `plain_job_key(unit["job"])`) ∈ wanted. **설정까지 맞춘다.**
   - 맞은 단위 수와 단계별 수가 파일의 `expected`와 다르거나 0이면 `SettingDefect("selection keys: …")`다. 10절 목록 밖이므로 census 상태가 setting_defect가 된다.
6. **입력 고정**
   - `--selection-keys`는 `PINNED_SHA256["selection_keys"]`(T8′ 상수, 생성된 파일 sha)로 `gate.pinned_input`을 거친다. 파일이 없으면 not_judgeable, sha가 다르면 setting_defect다.
   - census report의 `inputs.selection_keys`에 `pinned: true`를 넣는다. S8-C에는 census report sha(`<S8C_CENSUS_REPORT_SHA256>`)로 들어간다.
7. **보고**
   - 기존 `selection_cells`(병합 단위에 선택 단위 구성원이 하나라도 있으면 "선택 사용", rules:228-238)
   - `selection_units`(단위 id 18개)
   - `selection_non_units`(LSN4 1개, 없음 4개, 각각 역할)
   - 병합 뒤 선택 사용 병합 단위 수는 eps·해시 병합 때문에 18과 다를 수 있다. 기록만 하고 단언하지 않는다.
8. **0건·불일치의 도달 가능성**: 입력이 모두 sha로 고정돼 있고 아래 재생성 시험이 먼저 잡으므로, 6단계에서의 도달은 방어용이다.

### 3.4 시험
- **재생성**: 세 raw와 census 키(메인 checkout, `OUTRIGGER_RECORDS_ROOT=main`)로 생성기를 돌리면 파일 바이트 sha가 `PINNED_SHA256["selection_keys"]`와 같다. 이 시험은 핵심 시험이다. skip이면 판정 근거 미충족이다(`junit_skips --critical`에 `test_ed8_selection` 포함).
- **설정 대조**: 같은 plain job의 C-S VBNfast 합성 단위는 선택 사용이 아니다. VBNslow 단위는 선택 사용이다.
- 기대 수 불일치 → setting_defect. 0건 → setting_defect.
- 모르는 플랜트 접두 → 생성기 거부. r79 줄은 건너뛰고 셈한다.

---

## 4. R-2: 정체성 비교 범위(`ed8_settings`), 권고 = T8′에 넣음

### 4.1 근거
- 3.6(spec:162-163)의 정체성 목록에 `probe_k1_scale_settings`, `r8.lifted_reapproach`, `twist_completion_relax`가 있고 "어긋나면 setting_defect"다. 값은 3.3(δ 0.05 mm), 3.4((0.8, 3.6)), 3.7($T_r$ 0.5 s, $N_s$ 4), 3.8(Δ 2.5 kN, 여유 0.5 kN)이다.
- 지금 T8은 run_v5 줄에서 `hydraulic_options` 전체(스위치 3개)만 비교하고 수치는 보지 않는다. 생산자 가드 `check_last_ed8`(verdict_runs.py:887-888, harness_hydraulics.py:1270-1281)에 기대고 있다.
- r79 줄은 `p1_patch`만 본다(jp3_ed7_judge.py:407-411).

### 4.2 권고 내용
1. **run_v5 판 8 줄**(VBN, VBN0, LSN1~4, VBN<key>): 최상위 `ed8_settings`를 상수 `ED8_SETTINGS_EXPECTED`와 비교한다. 값은 명세 문면에서 가져온다.
   ```
   {"probe_k1_scale_settings": {"scale_mid_min_piston_travel_m": 5e-05},
    "r8": {"stiffness_warning_range": [0.8, 3.6],
           "lifted_reapproach": {"short_run_s": 0.5, "short_run_exit_samples": 4}},
    "twist_completion_relax": {"locked_drift_waiver": true, "waiver_max_rise_N": 2500.0,
                               "waiver_margin_N": 500.0}}
   ```
   - 실수는 상대차 ≤ 1e-12, 나머지는 완전 일치로 비교한다.
   - `ed8_settings`가 없거나 다르면 정체성 문제(setting_defect)다. 이것은 3.6 정체성 항목이고 10절 기록 실패 (1)(3.3·3.5·3.7·3.8 **기록 키**)이 아니다.
2. **r79 줄**(12b VBKN·VBKN0, l1ref): `r79_identity_view`의 meta 보충 필드에 `hydraulic_options.ed8_settings`를 더해, `options_of(setting)[1].to_dict()["ed8_settings"]`와 비교한다(A-4). 없거나 다르면 setting_defect다.
   - 수치 필드는 r79 줄과 meta에 없다(감사 R-1). 그래서 C8 코드 정체성(HEAD·03_src tree·단계 기록)으로 덮는다고 판정서에 적는다.
   - P8-15·P8-16의 r79 검토 팔(B_impl·L2_impl, VBKM0)은 설정이 아니므로 대상이 아니다. 그 정체성은 P8-16 해시 일치로 본다.
3. **시험**
   - 정체성 상수: `run_v5.options_of("VBN")` 경로가 만드는 config(`harness_hydraulics.check_ed8_config`를 통과하는 config)에 대해 `verdict_runs.ed8_settings_meta(config) == ED8_SETTINGS_EXPECTED`. 저장 출력은 fixture로 쓰지 않는다.
   - 어긋남 사례: δ 2.3 경고 범위, `short_run_s` None, waiver 꺼짐, 키 없음.
   - r79 meta 스위치 사례.
4. **위험**: 지금 결과가 없으므로 사후 도구 변경이 아니다. 41e107e9 사전 실행에서 r79 meta 8/8에 `hydraulic_options.ed8_settings`가 있었다(감사 B-1 근거 줄). 4단계 출력 뒤 M-5 키 존재 점검에 `ed8_settings`(run_v5 줄)를 더하기를 권한다.

---

## 5. 판정·기록 구분과 상태(새 항목만)
| 항목 | 구분 | 실패 시 | 도달 경로(코드) |
|---|---|---|---|
| 5단계 V0 정체성(1.3) | 판정(정체성) | setting_defect, $k$ 동결 안 함 | `judge_stage5` (b) |
| 5단계 입력 완결성 1356(A-1) | 판정 입력 | not_judgeable | `judge_stage5` (c) |
| 판 7 정체성 함수 예외(A-5) | 판정(정체성) | 그 줄 setting_defect | `identity_defects` |
| `ed8_settings` 수치(R-2), r79 스위치(A-4) | 판정(정체성) | setting_defect | `identity_defects`, r79 보기 |
| 선택 사용 키 칸 | 기록 | 입력 결함(sha·0건·기대 수 불일치) = setting_defect | `judge_census` |
| 12b 4사례 기록(사례 수·P-pred 입력·교착 서명) | 기록 | 입력 결함 = 기록 도구 setting_defect(12b 판정 상태 불변); 서명 None = 기록 실패 (3) | `four-case` |

상태 순서는 10절(판정 실패 > setting_defect > not_judgeable > 통과)을 따른다. 5단계는 (b)·(c)가 있으면 선택을 계산하지 않으므로 `stop`/`frozen`과 결함이 함께 나오지 않는다.

## 6. 판정서에 옮길 공개 문장(초안)
- **B-3**: "5단계 V0 줄의 정체성은 3.6 '기존 설정 그대로'에 따라 v5 기본 제어기다. 확인 항목은 `controller_tag` `final_C4G2_LAS_K1`, `hydraulic_options`·`hydraulics_record` 없음(③ 기록 없음), 판 6·7·8 기록 키 9개 없음, `job.setting` V0다(해석 결정, control-expert 2026-11-26). 저장 V0(main.jsonl)는 sha 고정으로 대신하고, 이 검사를 적용하지 않는다(그 줄에는 태그가 없다)."
- **M-4**: "8절 'P-pred 입력 통계'는 `jp3_12b_ppred.input_statistics`의 입력(K_c, N_c, a30, n_both, 사례별 (k_i, n_i), 뺀 줄 수, 재생 기회 줄 수, b4를 쓰면 K_TRw·N_TRw)으로 읽었다. 4사례를 뺀 값과 전체 값을 함께 기록하고 k_allow는 다시 계산하지 않았다. 사례 수는 틀 167에서 틀 안 4사례를 뺀 수다."
- **M-1**: "선택 사용 키는 P8-9·P8-9′·P8-14 raw(sha 머리말)의 run_v5 job을 플랜트 대응(VBM→VBN, VBMslow→VBNslow, LSM4→LSN4) 뒤 **설정까지 맞춰** census 단위와 대조했다. 단위 18(C-J 11, C-S 1, C-G 6), 단위 아닌 census 줄 1(LSN4), census 밖 4다. r79 13줄은 census에 해당하는 줄이 없어 뺐다."
- **R-2**: 4.2의 범위 문장(run_v5 줄은 수치 비교, r79 줄은 스위치 비교 + C8 코드 정체성).
- **F-1**: "T8 `four-case`의 사례 키 해석 결함(접두 `cand=current#`)을 T8′에서 고쳤다(감사 뒤 발견, control-expert)."

## 7. 가정
- V0 기대 태그는 오늘 코드에서 계산한 값(`final_C4G2_LAS_K1`)이다. C8 실행 경로 모듈은 T8과 바이트가 같다(P8-11 시험). 그래서 C8 실행에서도 같다고 본다. 확인은 4단계 이후 M-5 키 존재 점검(5단계 출력에도 `controller_tag`)으로 한다.
- 12b VBKN0 줄 키가 P8-14 r79 줄과 같은 꼴(`cand=current#`)이라는 것은 추정이다(같은 r79 도구). F-1 수정은 어느 꼴이든 맞게 동작한다.
- 4사례 = 계획 `faults` 키 4개라는 것은 기존 T8(`plan_cases`)과 spec:184-188의 4키 목록과 같다.

## 8. 위임 필요
- **python-expert(T8′, ed8-judge 위 새 커밋, C8 불변)**: 1.4·1.5(B-3, A-1, A-5, M-2 연동), 2.5·2.6(M-4, F-1), 3.3·3.4(M-1 생성기·파일·대조·시험), 4.2(R-2, 권고). 감사 B-1(가)·B-2와 함께 한다. 전체 시험에서 새 실패·새 skip 0, P8-11 시험을 다시 돈다.
- **메인**
  - `keys_selection_ed8/` 파일과 SUMS를 커밋한다.
  - 판정서 공개 문장(6절)을 쓴다.
  - verif-protocol-auditor T8′ 재감사 지시문에 이 결정문의 경로와 sha를 넣는다.
  - 감사 M-5 키 존재 점검 키에 `ed8_settings`(run_v5 줄), 5단계 출력의 `controller_tag`·`V0_ABSENT_KEYS`를 더한다.
- **verif-protocol-auditor(재감사)**: F-1 수정, 5단계 상태 순서((b)·(c)가 있으면 선택 미계산), 선택 키 대조를 설정까지 맞추는지 확인한다.

## 9. 수행한 작업
- **읽기**
  - 명세 S8-R 전체(1~449행), 감사 `verif_c8_t8.md`, `t8_report.md`
  - 코드(파일·줄 직접 지정)
    - ed8-judge: `jp3_ed8_judge.py`, `jp3_ed7_judge.py`(170-450), `run_v5.py`(440-530, 755-1050), `verdict_runs.py`(195-262, 291-449, 800-895), `harness_hydraulics.py`(1230-1294), `v5_options.py`(851-936, 1030-1066), `jp3_12b_judge_ed8.py`, `jp3_12b_judge_ed7.py`(1-175), `jp3_12b_judge_ed6.py`(1-60), `jp3_12b_ppred.py`(1-304), `jp3_12b_judge.py`(일부), `r79_L3L4_final.py`(125-199)
    - ed8-impl: `step5_heldout_v0_ed8.ps1`
- **실행**(PowerShell, `conda run -n dynamics-dev python -I -B`. V0 확인은 `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`=scratch). 스크립트는 `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\control-ed8-t8p\`에 있다(근거 스크립트, 메인이 근거 폴더로 옮길 대상).

| 스크립트 | sha256 앞 16자 | 내용 |
|---|---|---|
| `key_structure.py` | `A3AA0B37663C39A9` | raw 3개·census·held-out 키 구조와 대조 수 |
| `key_list.py` | `C3112EB6D82744C3` | 23 job의 정체(사례·위상·설정)와 census 역할 |
| `v0_identity_probe.py` | `687C6495B6D92498` | 프리셋 태그·스위치, `options_of("V0")`, 저장 V0 정체성 키 |
| `r79_key_form.py` | `465259623C4F06BD` | P8-14 r79 줄·계획 키의 접두 꼴 |

- **해시 확인**: 명세 `35f9eba8…2c121520`, raw 셋(3.1), census `278b332f…`, held-out `a18b5818…`가 모두 기대와 같다.

## 10. 공개(행위 그대로)
- **블라인드**: `j9_runs\606f8713\cdry_a1\…`, `prelaunch_j9\ed6_inputs\x11\selection.json`과 그 worktree 사본은 열지도 검색하지도 않았다. 그 상위 폴더(`j_p3_cause`, `j9_runs`, `prelaunch_j9`, `06_analysis`, worktree 루트)는 Grep·Glob 범위로 쓰지 않았다.
- **Grep·Glob 범위**
  - `ed8-judge\04_scripts\04_hydraulic\coupled`(파일 지정 또는 `glob *.py`/`jp3_12b*.py`)
  - `ed8-judge\04_scripts`(Glob `**/r79_L3L4_final.py` 한 번)
  - `ed8-judge\03_src\…\v5_options.py`
  - `ed8_design` 폴더(Glob `**/raw/runs.jsonl`, `**/census_keys_ed8.json`, `keys_seal_41e107e9/*`)
  - ed8-impl `run_steps_ed8\step5_heldout_v0_ed8.ps1`은 파일을 직접 지정해 읽었다.
- **raw 파일**: P8-9·P8-9′·P8-14 raw에서 job 필드 이름, 설정·팔 이름, job의 사례·위상·twin 식별 필드, r79 키의 접두 꼴만 출력했다. `commands_sha256`·지표·판정 값은 출력하지 않았다. 저장 main.jsonl V0 줄은 정체성 키 존재와 태그 값 분포만 셌다.
- **판정 도구 실행**: 판정 도구를 실제 결과에 돌리지 않았다. 코드 import는 `v0_identity_probe.py`의 상수 확인 한 번(프리셋 config, `options_of`)뿐이다. 실행 뒤 ed8-judge `status --porcelain --ignored`는 비어 있다.
- **셸**: Bash는 쓰지 않았다(파이프 없음). 프로세스를 종료하지 않았다. scratchpad는 `control-ed8-t8p\`만 썼고, 그 안 `numba` 하위 폴더만 지웠다.
- **에이전트 메모리**: `baseline-identity-and-record-keys.md`를 더하고 `MEMORY.md` 색인 한 줄을 더했다(V0 정체성 분리, 기록 도구의 키 해석 함수 공유, 설정까지 맞춘 선택 대조).

사용한 스킬: 없음
