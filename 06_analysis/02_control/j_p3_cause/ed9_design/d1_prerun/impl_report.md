# 판 9(436.9) 구현 1차 보고 (python-expert, 2026-11-28)

성격: 구현과 사전 진단만 했다. 판정은 하지 않았다. 판 9 규칙은 봉인 전이고, 규칙 문서는 쓰지 않았다.

## 0. 요약
- worktree `C:\workspace\outrigger_control\.claude\worktrees\ed9-impl`, 브랜치 `ed9-impl`. 기준은 T8⁗ `7ea78232`이다.
  - `git merge-base --is-ancestor 56849248 7ea78232` = 0: C8은 T8⁗의 조상이다. 반대 방향은 1이다.
  - 그래서 C8과 T8⁗을 모두 포함하는 커밋은 T8⁗ 자신이다.
- 커밋은 4개이고 모두 깨끗한 트리에서 만들었다.

| 커밋 | 종류 | 내용 |
|---|---|---|
| `320a1f641420573a1fb66c53aec36d421e42bb4d` | (a) 판정 도구 | 슬롯 키 (원천, 슬롯), 기준 층 고정 짝, 같은 형상 후보, J7 A, 5단계 기록 모드, `aa-candidates` |
| `2d843a332bfb20f6f88a5ea0984deaa23b007305` | (b) 제어기 | `two_pressure.py` C-m(클래스 기본 끔) + 단위 시험 |
| `b3dd2e9a2c1b1cba430a5a2d73a42ac98aebcce6` | 하네스 | `run_v5` 배치 `ed9_heldout_same_shape`(같은 형상 첫 후보 중 판 8이 돌리지 않은 7 job) |
| `9ec94e7a94b78832d3d7814aa3391d1b9f012506` | 판정 도구 | `stage5 --same-shape-rows`와 그 완결성 검사 |

- 판 8 5단계 출력을 고친 도구로 다시 돌린 스모크(기록)는 예측과 같다.
  - 슬롯 키만 고친 `ed8`: stop, N 11/310, E 0/24
  - `ed8_j7a`: N 3/310
- R1: 저장 V0에서 D1_step 사유가 있는 줄 수(S)
  - 5단계 V0 1356줄 중 8줄
  - census V0 main 100줄 중 0줄
  - 저장 격자 V0 768 run 중 0 run
- R2: Chrono ML 기록 재생에서 모든 과도 주기 도약 행이 C-m ≥ D1′이다. 조용한 주기는 100 %다. 실제 도약 거짓 FAULT는 C0·C-m 모두 0이다.
- R3·R4는 띄우지 않았다. 다만 바로 띄울 수 없다.
  - C-m을 하네스에서 켜는 경로(프리셋·태그·옵션)가 아직 정해지지 않았다(확인 필요 1).
  - R4에 필요한 판정 커밋 상수(`RUN_COMMIT`)가 아직 C8이다.

## 1. 커밋 (a) 판정 도구 `320a1f64`
파일: `04_scripts/04_hydraulic/coupled/jp3_ed8_rules.py`, `jp3_ed8_judge.py`. 판 8 파일을 그 자리에서 고쳤다. 판 8 동작은 `--rule-set ed8`(기본값)로 남긴다.

- **슬롯 키 (원천, 슬롯)**: 종료 판정서 4.1 표의 모든 위치를 고쳤다.
  - `rules.slot_id(source, slot)` = `<source>|<slot>`이다.
  - 판정 도구가 만드는 슬롯 입력의 `slot`, 8단계 단위의 `id`·`slot`을 이 값으로 바꿨다.
  - 그래서 짝 사전(464), `_layer_counts`(440), `aa_summary`(426), `slot_layers`(468), 합침 경로(484), `first_aliases`(462), 8단계 별칭(544·551), `_unit_layer`(584-589), eps 병합 행 키(558), `members`(180)가 모두 결합 키로 묶인다.
  - `aa_shape_record`(892-897)와 기록 문구(1269·1277·1285)도 결합 키를 쓴다.
  - 단언을 넣었다.
    - `stage5_selection`과 `heldout_judgement`는 식별자가 반복되면 `RuleInputError`로 거부한다.
    - 5단계는 `slot_count = len(slot_layers) + len(first_aliases) = 키 줄 수`, 8단계는 `unit_count + 건너뛴 줄 = 키 줄 수`를 단언한다. 어긋나면 `RecordCountError`(종료 3)다.
- **`--rule-set`**(census·stage5·heldout·aa-candidates)
  - `ed8`: T8⁗ 해석 + 슬롯 키 수정(기본값)
  - `ed8_j7a`: `ed8` + J7 닫힌 목록
  - `ed9`: J7 닫힌 목록 + 기준 층 고정 짝 + 같은 형상 후보 순서
- **기준 층 고정 짝**(`PAIRING_BASE_LAYER`, stats 2.2)
  - 순서의 첫 후보 하나를 짝으로 쓰고, 기준 V0(o) 층에서 센다. 재시도는 없다.
  - 후보 자신의 층은 `candidate_layer`로 기록만 한다.
  - 같은 해시면 제외하고 기록한다. 다음 후보로 넘어가지 않는다.
  - 기준 통과 슬롯의 후보 줄이 없으면 `candidate_not_run`이다. 이 경우 판정 불가이고, "기회 없음"으로 읽지 않는다.
- **같은 형상 후보**(stats 3.1): `aa_order_of`가 조건과 `effective_shape`가 같은 후보만 키 순서대로 남긴다. `a_phase`·`c_fs`에서는 아무것도 걸러지지 않는다.
- **J7 A**(`J7_CLOSED_LIST` = `WARN_D1_IMU_GYRO_MISSING`, `WARN_D1_IMU_INPUT_MISSING`)
  - 해당 J7 실패를 기록(`closed_list_records`)으로 내린다. 목록 밖 경고는 그대로 실패다.
  - 적용 범위: C-J (i), A/A 짝, G′(8단계)
  - 적용하지 않은 곳: C-S와 C-J (ii) LSN 줄 수(확인 필요 2)
- **5단계 기록 모드**(`aa_breakdown`): 층마다 원천·조건 위상·후보 위상·형상(조건→후보)·항목군별 x·n을 낸다.
  - 항목군 정의(`ITEM_GROUPS`)
    - 목록 경고: J7 닫힌 목록. 실패든 기록이든 센다.
    - FAULT: J4, 또는 J7의 `FAULT_*`
    - 연속 항목: J2·J5·J6·J8
    - 기타
- **`aa-candidates`**: 키 파일만 읽는다. `ed9` 첫 후보 목록(`aa_order` 색인, 5단계 배치가 이미 돌렸는지)을 낸다. 판정이 아니다.
- 시험
  - 새 `05_tests/unit/test_ed9_judge_tool.py`(24개, 커밋 (d)에서 27개)
    - 이름이 같고 원천이 다른 합성 슬롯
    - 실제 키 파일에서 끝까지 도는 시험(CWD는 다른 폴더). 기록 항목 339와 상태 분류를 전부 단언한다.
  - 기존 시험의 합성 키 줄에 `source`를 넣었다(`test_ed8_judge.py`, `test_ed8_t8pp_records.py`).
  - 부모 범위 시험 `test_ed8_gate_p80_key::test_changes_since_t8ppp_are_the_gate_and_tests_only`를 T8‴→T8⁗ 고정 범위로 바꿨다.

## 2. 커밋 (b) 제어기 `2d843a33`
파일: `03_src/outrigger_sim/control/two_pressure.py`

- 설정 `TwoPressureSettings.imu_residual_median_check: bool = False`
  - 클래스 기본값이 꺼짐이라 옛 피클은 꺼짐으로 읽힌다.
  - meta 키는 켰을 때만 생긴다.
- 상태 `_d1_reference_pairs`
  - 클래스 수준 기본값은 None이고, 켰을 때 첫 읽기에서 만든다. 꺼져 있으면 상태가 생기지 않는다.
  - 최근 3주기 (ΣF, f_z)를 보관한다.
  - D1″를 쓸 수 없는 주기가 오면 비운다. 조건은 `explained_imu`, 크롤러 이탈(재접촉 의심 중이면 제어기가 False를 넘김), f_z 있음, 유한값이다. `reset`도 비운다.
- 판정
  - C0이 설명하지 못한 다리에 한해, `|r_j − med(r_{j−1..j−3})| < 0.5|Δp_h|A_p`이면 `INFO_PRESSURE_STEP:<leg>:head:imu_residual_median`로 설명한다.
  - 기준 잔차는 그 주기의 `M_eff`로 다시 계산한다.
  - 유효 기준이 3개 미만이면 C0만 쓴다.
  - D1″에만 적용하고 D1′(합 규칙)에는 적용하지 않는다.
- 시험 `05_tests/unit/test_two_pressure_d1_median.py`(18개)
  - 세 표본 가짜 FAULT 꼴: C0은 FAULT, C-m은 설명함
  - 지속 도약 ±100.5·±150 bar: 같은 주기에 FAULT
  - 한 표본 스파이크: 같은 주기에 FAULT
  - k+2 꼴: C-d라면 설명되지만 C-m은 FAULT
  - 기준 3개 미만, 접지 주기가 끼어 끊긴 경우: C0
  - 질량 일관성: 기준을 현재 `M_eff`로 다시 계산한다
  - 스위치 끔: `git show 56849248`로 C8 모듈을 따로 올려 같은 각본을 돌리면 events·forces·meta가 비트 단위로 같다
  - 스위치 켬: D1_step FAULT가 없는 각본은 결과가 같다(P9-D1-2 전제)
  - 피클 2종
- C9 가지에서는 `03_src`를 일부러 바꾸므로, 판 8 P8-11 시험 3개를 T8⁗ 고정으로 바꿨다(HEAD 대신 `7ea78232`).
  - `test_ed8_run_path.py` 2개
  - `test_ed8_gate_p80_key.py::test_working_tree_changes_since_c8_stay_off_the_run_path`
  - 이 판정 근거 시험의 변경은 verif 확인 대상이다(확인 필요 7).
- 프리셋·태그에는 넣지 않았다. 후보는 확인 필요 1에 적었다.

## 3. 커밋 (c)·(d) 같은 형상 후보 실행 경로 `b3dd2e9a`, `9ec94e7a`
- 사용자 결정("같은 형상 후보가 없는 슬롯만 새로 돌림")을 실행할 경로다.
- `run_v5` 배치 `ed9_heldout_same_shape`(`--jobs-file heldout_g_ed8.json`)
  - b_shape 슬롯 가운데 같은 형상 첫 후보가 `aa_order` 색인 2 밖에 있는 경우만 돈다. 봉인 키에서는 7 job이다.
  - 기존 배치와 import 폐포는 바뀌지 않는다.
- 판정 도구 `stage5 --same-shape-rows/--same-shape-step-done`
  - 판정 도구의 목록(`aa_candidate_list`)과 하네스 목록이 다르면 setting_defect다.
  - 줄이 빠지거나 겹치거나 남으면 판정 불가다.
- 시험 +3: 두 목록이 같음, ed9 끝까지 돌림(판정 가능), 한 줄 빠짐(판정 불가)

## 4. 시험 결과
| 명령(worktree 루트, `PYTHONDONTWRITEBYTECODE=1`, `OUTRIGGER_RECORDS_ROOT=C:\workspace\outrigger_control`) | 결과 |
|---|---|
| dynamics-dev `python.exe -m pytest -q -p no:cacheprovider`. 대상: test_ed9_judge_tool, test_ed8_judge, test_ed8_t8pp_records, test_ed8_t8pp, test_ed8_t8p, test_ed8_run_path, test_ed8_judge_rules, test_ed8_jp3_settings, test_ed8_gate_judge, test_ed8_gate_p80_key, test_ed8_impl, test_ed8_run_commit | **342 passed, 0 skip**(HEAD `9ec94e7a`) |
| Chrono-dev 같은 옵션. 대상: `test_two_pressure*.py` 전체, test_c2_r8d1, test_c2_r6, test_sample_period_copies, test_ed8_run_path, test_ed8_gate_p80_key | **412 passed, 49 skipped**(`07_results` 저장 자료 없음) |
| `tools\verif\worktree_tests.py --data-root <메인> --python Chrono-dev`. 대상: test_two_pressure_d1_imu, d1_steps, d1_median. probe 모듈 `outrigger_sim.control.two_pressure` | pytest 117 passed, **skip 0**, probe=worktree, 원본 불변. **도구 종료 1**: 경고 7건(`data_literal_not_rebased`)이고 실패가 아니다 |
| ruff(프로젝트 설정 줄 길이 100), codespell | 변경 파일은 통과. 기존 위반 3건(`run_v5.py:1075·1080·1084` E501)은 고치지 않았다 |

- 기존 실패나 xfail은 없다.
- 검증 공백
  - Chrono-dev skip 49건 가운데 23건은 다시 돌리지 않았다. d1 세 파일 밖의 `test_two_pressure_*`·`test_c2_*` 저장 자료 시험이다. 스위치를 끈 경로라 동작 변경은 예상하지 않는다.
  - 커버리지는 재지 않았다.

## 5. 판 8 5단계 출력 재판정 스모크(기록, 판정 아님)
- 출력: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed9_design\d1_prerun\judge_smoke_320a1f64\`
  - `stage5_{ed8,ed8_j7a,ed9}.json`과 각 `.console.txt`(시작·끝 시각, 종료 코드)
  - `aa_candidates_ed9.json`
  - 실행 명령 `run_smoke.ps1`, 요약 `summarize_smoke.py`
- 실행: dynamics-dev `python.exe -I -B`, 판정 도구 커밋 `320a1f64`
- 입력: `ho_v0/aa2/aa3_a1/*.jsonl`과 `ho_*.done`, 키 파일, `confirm_b_grid192.json`
  - jsonl은 도구만 읽었다. 나는 상태·사유·층별 건수만 출력했다.

| rule-set | 종료 | status | 사유 | E (x/n_aa, n) | N (x/n_aa, n) | 기록 수 |
|---|---|---|---|---|---|---|
| ed8 | 1 | stop | N A/A CP95 0.058051 > 0.025 | 0/24, 24 | **11/310**, 312 | slot_count 339 = layered 339 |
| ed8_j7a | 0 | frozen | – | 0/24, 24 | **3/310**(CP95 0.024821), 312 | 339 |
| ed9 | 2 | not_judgeable | 기준 통과 슬롯 7개의 A/A 후보가 실행되지 않음 | 0/23(기록) | 1/306(기록) | 339 |

- `ed8`의 N 11 = 원천별 `a_phase` 4 + `b_shape` 3 + `c_fs` 4다. 항목군으로 보면 목록 경고 8, 연속 3, FAULT 3, 기타 3이다(한 짝이 여러 군에 걸칠 수 있음).
- `ed9`는 같은 형상 후보 7개(b_shape, `aa-candidates` 7 job)가 없어 판정 불가로 끝난다. 표의 수는 일부 슬롯만 센 기록이다.
- 원인 분석의 고유 이름 재계산 파일(`rerule_unique_names.json`)은 열지 않았다. 대조는 공개 문서의 수(11/310, 0/24, 3/310)와만 했다.

## 6. R1 저장 V0 D1_step 스캔
- 출력: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed9_design\d1_prerun\scan_d1_step.json`
- 스크립트: `...\d1_prerun\scripts\scan_d1_step.py`
- 이벤트 이름만 읽는다. 키 목록과 건수만 쓴다.

| 묶음 | 줄 | D1_step 줄(S) | FAULT_HEAD 줄 | 사유 없는 FAULT_HEAD |
|---|---|---|---|---|
| 5단계 V0(ho_v0+aa2+aa3) | 1356 | **8** | 8 | 0 |
| census V0 `06_analysis/03_hydraulic/coupled/v5/main.jsonl`(V0 줄) | 100 | 0 | 0 | 0 |
| 저장 격자 V0(confirm_b_grid192 + census 키의 v0_pair 파일, 4개) | 768 run | 0 | 0 | 0 |

- 형식 함정: 결과 줄의 `event_names`에는 이름이 첫 `:` 앞까지만 남는다. 사유 전체 이름은 `event_output.warnings`에 있다.
  - 처음 두 번은 이 필드를 보지 않아 0으로 나왔다.
  - 그 두 출력은 내가 만든 직후 지우고 다시 만들었다.
- census main의 events가 200 상한에 걸린 줄은 0이다. `event_names`의 `FAULT_HEAD_PRESSURE`도 0이다(교차 확인).

## 7. R2 Chrono ML 기록 재생 주입
- 출력: `...\d1_prerun\ml_inject_cm.csv`(sha256 앞 16자리 `48A8E4C264CD9623`), `ml_inject_cm.provenance.json`
- 스크립트: `...\d1_prerun\scripts\ml_inject_cm.py`
- 방식
  - 개루프 기록 재생이다(s8ml2_jump_inject.py 방식). 피클은 열지 않았다.
  - 대상은 에피소드 192개다.
  - 자이로 보정을 켰다. 자이로 기록이 있는 에피소드는 7개이고, 레버 팔은 YAML의 오거 단계 질량중심으로 잡았다(top 3, bottom 3, middle 1). 나머지 185개는 보정 없음이다.
  - C-m의 기준 유효 조건은 직전 주기 위상이 들림 상태이고 값이 유한한 것이다.

| 주입 | 주기 | 후보 | D1′ | C0 | **C-m** | C-m ≥ D1′ | 조용한 주기 100 % |
|---|---|---|---|---|---|---|---|
| −150 | 과도 | 1004 | 98.71 % | 100.00 % | **99.90 %** | True | |
| −100 | 과도 | 537 | 93.48 % | 98.14 % | **97.58 %** | True | |
| +100 | 과도 | 582 | 93.13 % | 96.22 % | **95.53 %** | True | |
| +150 | 과도 | 1011 | 98.22 % | 100.00 % | **100.00 %** | True | |
| ±100·±150 | 조용 | 104,271~214,684 | ≥ 99.999 % | 100 % | **100 %** | True | True(4행) |
| 실제 도약(주입 없음) | 과도 | 17 | 3 FAULT | 0 | **0** | | |

- P-S8-14 (c) 기준(C-m ≥ D1′, 각 과도 도약 행)과 조용한 주기 100 %를 모두 충족한다.
- C0 대비 손실은 0~0.69 %p다(−100 bar 0.56, +100 bar 0.69). 이 값을 P9-D1-6에 어떻게 대조할지는 stats·control이 정한다.
- 자체 확인: 합성 3사례로 규칙 함수를 확인했다(가짜 FAULT, k+2, 기준 부족). 3/3 통과다.

## 8. P9-D1-1·2용 비교 도구(R3 다음에 씀)
- `...\d1_prerun\scripts\compare_identity.py`
  - 저장 줄과 새 줄을 job마다 비교한다. 비교 항목은 `commands_sha256`, `final_phase`, WARN/FAULT 이름 집합이다. 이름은 `event_names`, `events`, `event_output.warnings/fault_events`에서 모은다.
  - `--allowed-from scan_d1_step.json`을 주면 S 밖에서 바뀐 줄이 있을 때 `differs`(종료 1)다.
  - 줄이 빠지거나 0건이면 판정 불가(종료 2)다.
  - 출력에는 `allowed_unchanged`(바뀌지 않은 S 줄 수)가 있다. P9-D1-3을 볼 때 쓴다.
- 자체 확인
  - 합성 5사례 통과
  - 5단계 1356줄을 자기 자신과 비교: `identical`, allowed 8. 이 출력은 scratchpad에 두었다가 지웠다.

## 9. 메인 세션 권고(띄우지 않음, R3·R4)
선행 조건 세 가지:
1. C-m 하네스 스위치 경로를 정하고 구현한다(확인 필요 1). 그 커밋을 C9로 둔다. C9 고정 worktree는 예를 들어 `.claude\worktrees\ed9-c9`로 만들고 잠근다.
2. R4용 판정 커밋 T9: `jp3_ed8_gate_judge.RUN_COMMIT`(지금 C8)과 SPEC sha를 C9와 판 9 규칙으로 바꾼다. 지금 상태로는 C9 출력의 `.done`을 `checked_step`이 거부한다.
3. 인터프리터 호출 방식(`conda run -n dynamics-dev` 대 dynamics-dev `python.exe` 직접)을 5단계 identity 기록과 같게 한다. 나는 그 기록(`ho_*_a1` 폴더 안, `.done`, 5단계 러너)을 열지 않았다(확인 필요 6).

러너: `~/.claude/runners/outrigger-ed9-r3/`. `.done`은 판 8과 같은 Complete-Step 꼴(종료 0, 커밋, 끝 identity가 깨끗함, 출력이 폴더 안)로 남긴다. compute-scheduler 배치, 예약, long-running-task-monitor 점검을 따른다.

| # | 명령(C9 worktree 루트, `<py>` = 3의 호출 방식, `$K` = `...\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json`) | 출력 | 예상 시간과 근거 |
|---|---|---|---|
| R3a 끔 | `<py> -I -B 04_scripts/04_hydraulic/coupled/run_v5.py ed8_heldout_v0 --jobs-file $K --workers <N> --mask <HEX> --out <O_a>\ed8_heldout_v0.jsonl`. 같은 꼴로 `ed8_heldout_aa2`, `ed8_heldout_aa3` | `ed9_design\d1_prerun\r3a_off_<C9>\` | 1356 run 약 57분(5단계 실측 10:44:17~11:41:39, 같은 worker·마스크일 때) |
| R3a 대조 | python-dev `compare_identity.py --stored <5단계 3파일> --new <O_a 3파일> --out <O_a>\identity_off.json` | 같은 폴더 | 수 초. 기대: `identical`, 종료 0 |
| R3b 켬 | 스위치를 켜고 R3a와 같은 3배치. 여기에 `run_v5.py ed9_heldout_same_shape --jobs-file $K --out <O_b>\ed9_heldout_same_shape.jsonl`(7 run)을 더한다 | `...\r3b_on_<C9>\` | 약 57분 + 약 1분 |
| R3b 대조 | `compare_identity.py --stored <5단계 3파일> --new <O_b 3파일> --allowed-from ...\d1_prerun\scan_d1_step.json --out <O_b>\identity_on.json` | 같은 폴더 | 기대: `as_expected`, differing ≤ 8, `allowed_unchanged` 0(P9-D1-3) |
| R3c 진단 | 진단 7 job + 경계 훑기 54 job(켬) | `...\r3c_diag_<C9>\` | 약 10분(control 추정, 4 worker). job 목록은 `stage5_aa_diag` 쪽에 있다. 나는 열지 않았다(위임) |
| R4 | T9에서 dynamics-dev `jp3_ed8_judge.py stage5 --rule-set ed9 --keys $K --grid-keys ...\ed6_design\keys\confirm_b_grid192.json --grid-root <메인> --v0-rows <O_b 3파일> --step-done <각 .done> --same-shape-rows <O_b>\ed9_heldout_same_shape.jsonl --same-shape-step-done <.done> --out ...\d1_prerun\r4_<T9>\ho_k_selection.json`. 같은 꼴로 `--rule-set ed8_j7a`(기록) | `...\r4_<T9>\` | 수 초 |

합계는 약 2시간 10분이다.

## 확인 필요
1. **C-m 하네스 스위치 경로**(control 확인 필요 3). 지금은 `TwoPressureSettings` 필드뿐이고 하네스에서 켤 길이 없다. 후보:
   - (가) `C2Config.with_10hz_d1(...)` 인자 + V0 태그 접미사. 예: `final_C4G2_LAS_K1_CM`, ③ 쪽 `_P3_` 짝. 판정 도구의 `V0_CONTROLLER_TAG` identity, 태그 접미사 판별(`is_extend_start_tag` 계열), A/A 후보 V0 판별에 반영해야 한다.
   - (나) run_v5 실행 옵션. job key는 그대로 두고 줄의 controller meta에만 남긴다. 켬·끔 줄이 같은 job key라 출력 폴더로만 갈린다. 섞일 위험이 있다.
   - (다) 클래스 기본값을 켬으로 바꾼다. V0 정의가 바뀌어 전 줄을 다시 만들어야 하므로 사용자 결정(저장 줄 재사용)과 충돌한다.
2. J7 A 적용 범위: C-J (i)·A/A·G′에만 적용했다. C-S(민감도 4설정)와 C-J (ii) LSN 줄 수는 그대로다. 규칙 문면에 범위를 적어야 한다.
3. 항목군 정의(ITEM_GROUPS)가 stats의 "목록 경고 / FAULT / 연속 항목" 뜻과 맞는가. 특히 FAULT = J4 또는 J7 `FAULT_*`로 둔 부분.
4. 기준 층 짝에서 같은 해시인 경우: 제외하고 기록, 재시도 없음(`AA_SAME_HASH_TRIES_NEXT=False` 유지). 규칙 문면이 필요하다.
5. ed9 5단계 구성: 사용자 결정(저장 1356줄 + 같은 형상 7 job)대로 구현했다. stats R-2(같은 경로로 678 run을 새로 실행)와는 다르다.
6. R3 인터프리터 호출 방식이 5단계 identity 기록과 같은지. 메인 세션이나 verif가 확인한다.
7. 판 8 판정 근거 시험 4개를 T8⁗ 고정 범위로 바꿨다(1·2절). 의미는 보존했다고 판단하지만 verif 확인 대상이다.

## 위임 필요
- control-expert: 확인 필요 1(스위치·태그 이름), R3c 진단 job 목록의 소유와 경로(`stage5_aa_diag`, 나는 열지 않음)
- stats-design-expert: 확인 필요 2·3·5, R2 결과와 P9-D1-5·6 허용폭
- verif-protocol-auditor: 판정 도구 변경 감사(4.1 전 위치, 기록 수 단언, 합성 충돌 시험), 재고정한 시험 4개, `same_shape_completeness`
- 남은 python 몫(이번에 하지 않음): `tools/verif` `record_check --list-key`·`gate_scan` `dict_keyed_by_record_field`(종료 판정서 4.1), 5단계 해시 재생 동일성 판정, T9 상수 교체

## 공개(실제 행위)
- **Read**
  - 지시 명세 두 개 전체
  - 종료 판정서 1~60·184~335행
  - decision_log 835행
  - 5단계 판정서 113~212행(2절)·341~365행(7절)
  - 4단계 판정서 336~375행(6절): 금지 목록을 알려고 읽었다. 이 두 판정서는 경로 2 금지 목록에 들어 있다.
  - 내 worktree의 판정 코드(`jp3_ed8_rules.py` 전체, `jp3_ed8_judge.py` 대부분, `jp3_ed7_judge/rules`·`jp3_j9main_judge`·`judge_stage1_4368`·`ed8_key_lists`·`run_v5` 일부)
  - 그래서 **나는 판 9 경로 1 작성자다. 경로 2 작성자가 될 수 없다.**
- **Glob**(파일 이름이 보였다): `j9_runs/56849248/ho_*_a1/*.jsonl`, `judge_7ea78232_s5/*`, `ho_*.done`. `j9_runs` 상위 폴더는 검색 범위로 쓰지 않았다.
- **값 없는 probe**(ho_* jsonl을 스크립트로 읽음): 키 경로, 숫자·다리를 가린 이름 꼴, 건수만 출력했다. 결과는 `event_output.warnings` 안의 사유 문자열 10개(8줄)였다.
- **스모크**: 판정 도구가 ho_*와 `.done`을 읽었다. 출력 json에는 슬롯별 A/A 판정이 있다. 나는 층·원천·항목군 건수만 출력했다. `judge_7ea78232_s5`는 읽지 않았다.
- **열지 않은 것**: ed8-impl·ed8-judge4·ed8-diag worktree, `stage5_aa_cause/`·`stage5_aa_diag/`·`stage5_prejudge/`·러너, P8-2 경로 2 자료
- **지운 것**
  - 내가 만든 R1 첫 두 출력과 R2 첫 출력: 필드 누락이나 레버 팔을 고쳐 다시 만들었다. 결과 수는 R2 첫판과 같았다.
  - scratchpad `python-ed9impl\` 전체
- Bash 파이프·heredoc을 쓰지 않았다. 프로세스를 종료하지 않았다. 병렬 실행은 하지 않았다(pytest `-n` 없음).
- **경로 2 금지 목록 추가 후보**: `ed9_design/d1_prerun/judge_smoke_320a1f64/`(슬롯별 A/A 판정), `scan_d1_step.json`(5단계 FAULT 줄 키), `ed9-impl` 브랜치의 판정 코드

## 메모리 반영안
- `tool_run_v5_line_event_fields.md`: 결과 줄의 `event_names`는 첫 `:` 앞까지만 남는다. 사유 전체 이름은 `event_output.warnings`에 있다. 세기 전에 키 경로 probe를 먼저 한다(MEMORY.md에 한 줄 더함).

## 의존성 점검·사용한 도구
- 의존성 점검: STAMP(이 세션에서 이미 점검함)
- 사용한 스킬: 없음
- 설치함: 없음
