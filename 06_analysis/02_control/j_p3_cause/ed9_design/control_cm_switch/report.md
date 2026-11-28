# 판 9(436.9) C-m 하네스 스위치 경로, R3c 진단 job, R2 대 P9-D1-6 검토

작성: control-expert, 2026-11-28.
- **성격**: 판 9 설계 입력이다. 판정이 아니고, 봉인 전 문서다.
- **한 일**: 코드 읽기(구현 worktree `ed9-impl`, HEAD `9ec94e7a`), job 목록 대조, R2 CSV 재계산을 했다.
- **하지 않은 일**: 시뮬레이션 실행, 코드 수정을 하지 않았다. 판정 출력은 열지 않았다.

## 0. 요약

**1. 스위치 경로: (가′)를 추천한다.** (가)의 프리셋 인자와 태그 접미사를 쓰되, 켜는 수단은 **배치에 묶인 실행 스위치**로 한다(job key는 그대로).
- 구성
  - `with_10hz_d1(imu_residual_median_check=False)` 인자를 둔다. 프리셋 기본은 끔이다.
  - 판 9 배치 이름(예: `ed9_heldout_v0`)이 그 프로세스의 모든 프리셋에서 C-m을 켠다.
  - 태그는 run 자신의 설정에서 붙인다(`with_switch_tags`).
- 태그: V0 `final_C4G2_LAS_K1_CM`, ③ 짝 `final_C4G2_P3_LAS_K1_CM`, VBN `final_C4G2_P3X_LAS_K1_LSB_CM_ED8`, VBN0 `final_C4G2_LAS_K1_LSB_CM_ED8`.
  - `_CM`은 `_TCL` 뒤, `_ED8` 앞에 둔다. 그러면 `_ED8`이 늘 끝이라는 기존 계약(`is_ed8_tag`가 `endswith`로 판별)이 깨지지 않는다.
- (다)(클래스 기본 켬)는 쓰지 않는다. 프리셋 기본 켬도 쓰지 않는다. 두 경우 모두 옛 피클, 모든 러너, 논문 v5(현 v5 제어기로 닫기로 한 11-28 결정)의 실행까지 바뀐다.
- (나)를 그대로(job key와 출력 폴더로만 구분) 쓰면 두 구멍이 생긴다.
  - 이어 돌리기(resume) 검사(`run_v5.py:1010-1048`)가 저장된 C-m 끔 줄을 C-m 켬 실행에서 "끝난 job"으로 센다.
  - spawn worker는 부모 프로세스의 플래그를 물려받지 않는다.
- **판정 도구에서 꼭 고쳐야 할 곳**: `v5_options._split_tail`(`v5_options.py:887-903`)이 `_CM`을 떼게 해야 한다.
  - 떼지 않으면 `..._CM_ED8`에서 `switch_base_tag`가 `final_C4G2_P3X`를 찾지 못한다. 그러면 `extend_start_revision_of_tag`이 None이 되고, VBN 줄의 J-P3 판정 행이 0이 된다(`j_p3_inputs.py:147`, `jp3_j9main_judge.py:284-297`).
- **VBN(처리 팔)에도 똑같이 켜야 한다**(모든 팔 공통 감시기). 한쪽 팔에만 켜면 가짜 FAULT 제거 효과가 처리 효과로 섞인다.

**2. R3c**
- 진단 job은 python-expert가 만들었다(ed8-diag worktree, 커밋하지 않은 trace 패치). 목록은 세 파일이다.
  - `ed8_design\stage5_aa_diag\diag_jobs.json`(7)
  - `diag2\jobs_sweep.json`(34)
  - `diag2\jobs_sweep_ext.json`(20)
- **정오**: 이름(label)은 61개, 고유 job은 59개다. 이전 보고의 "고유 job 61"은 틀렸다. J1 ≡ J1shape_o0.0875이고, J3 ≡ J3shape_o0.0875다.
- 59개 중 5개(J1, J4, S1, S2, S3)는 R3b(5단계 1356줄)에도 들어 있다. 54개는 R3c에만 있다. `ed9_heldout_same_shape` 7 job과 겹치는 것은 없다.
- 기대값
  - C0에서 D1_step FAULT가 난 고유 job 9개: 같은 결정 주기에 `INFO_PRESSURE_STEP:<leg>:head:imu_residual_median`으로 바뀐다. 둘째 비교의 비는 ≤ 0.078(자이로 없음)이다.
  - 나머지 50개: 저장된 진단 줄과 비트 동일하다.

**3. R2**
- C0 대비 손실은 1/1004, 3/537, 4/582, 0/1011건이다. 점추정 0.10 / 0.56 / 0.69 / 0 %p, 한쪽 95 % CP 상한 0.47 / 1.44 / 1.57 / 0.30 %p다.
- k1을 포함한 전체 주기로 셈해도 3 %p 아래다. 그래서 P9-D1-6을 보수적으로 읽어도 충족한다.
- 다만 R2는 구간(k1 / k2 / late)을 나누지 않았다. 에피소드 안의 상관도 반영하지 않았다. 그래서 "k1 밖" 정의 그대로 대조하려면 구간 열을 더해야 한다.
- P9-D1-5(C-m ≥ D1′)는 모든 과도 행에서 +1.2~+4.1 %p 차로 충족한다.

## 1. 질문 1: C-m을 하네스에서 켜는 경로

### 1.1 코드 사실(ed9-impl `9ec94e7a`)
| 사실 | 위치 |
|---|---|
| V0 줄에는 v5 옵션이 없다(`hydraulic_options` null). 제어기 옵션은 `apply_controller_options`로만 들어간다 | `run_v5.py:123`(`"V0": (False, {})`), `run_v5.py:950`, `v5_options.py:797-815` |
| `apply_controller_options`는 옵션이 있는 설정(VBN 등)에만 걸린다. 옵션을 설치하는 래퍼는 `C2Config.with_10hz_d1`을 프로세스 안에서 바꿔 끼운다 | `verdict_runs.py:844-852`(`hydraulics.is_any_on`일 때만), `harness_hydraulics.py:1197-1218` |
| 그래서 C-m을 `HydraulicOptions` 필드로 두면 V0에는 켜지지 않는다. V0에 옵션을 주면 V0 정체성(`hydraulic_options` null) 관문을 어긴다 | `jp3_ed8_judge.py:280-282` |
| 태그는 run 자신의 C2 설정에서 붙는다. LAS-b·K1·LSB·TCL·ED8 판별 함수가 순서대로 접미사를 더한다 | `v5_options.py:1033-1066`, `verdict_runs.py:434-443`(T4h), `verdict_runs.py:871-877`(옵션 없는 run) |
| 접미사 해체 `_split_tail`은 `_ED8`, `_TCL`, `_LSB`만 안다 | `v5_options.py:887-903` |
| ③ 판별(`is_extend_start_tag`, `extend_start_revision_of_tag`)은 `switch_base_tag`가 접미사를 다 뗀 결과로 한다 | `v5_options.py:1002-1030` |
| `is_ed8_tag`는 `endswith("_ED8")`로 판별한다 | `v5_options.py:997-999` |
| job key에서 빠지는 runtime 키는 `mask`, `t4h_dir`뿐이다 | `run_v5.py:800`, `run_v5.py:809-811` |
| 이어 돌리기 검사는 `hydraulic_options`만 비교한다(태그나 C-m 상태는 보지 않는다) | `run_v5.py:1010-1048` |
| C-m 설정은 `TwoPressureSettings.imu_residual_median_check`(클래스 기본 False)이고, meta 키는 켰을 때만 생긴다 | `two_pressure.py:567`, `two_pressure.py:931-932` |
| `TwoPressureSettings`를 기본값으로 새로 만드는 프리셋 경로는 없다. 모두 `replace`라서 C-m 값이 뒤 단계(③, LSB, ED8)를 지나도 남는다 | `TwoPressureSettings(` 생성은 `two_pressure.py:1426` 한 곳(control 폴더 Grep), `v5_options.py:818-825`, `c2.py:2964-2969` |

### 1.2 세 안 비교
| 안 | V0에 켜지나 | VBN에 켜지나 | 저장 줄 재사용 | 위험 |
|---|---|---|---|---|
| (가) 문자 그대로: 프리셋 인자 + 태그 | 인자를 넘길 호출자가 없다. 하네스 호출자는 `with_10hz_d1()`을 인자 없이 부른다 | 같음 | 가능 | 켜는 수단이 따로 필요하다 |
| (나) run_v5 실행 옵션, job key 그대로, meta만 | worker에 전달되면 켜진다 | 같음 | 가능 | spawn worker가 부모 플래그를 받지 못한다. 이어 돌리기가 끔·켬 줄을 섞는다(`run_v5.py:1010-1048`). meta를 쓰지 않는 판정 도구는 구별하지 못한다 |
| (다) 클래스 기본 켬 | 켜짐 | 켜짐 | V0 정의가 바뀐다 | 옛 피클 복원(`refresh_settings`, `two_pressure.py:1533-1540`), Chrono·ML 러너, 논문 v5 A형 실행이 모두 바뀐다(11-28 "현 v5 제어기로 v5를 닫음"과 충돌). 프리셋 기본 켬도 같은 문제다 |
| **(가′) 추천**: 프리셋 인자 + 배치에 묶인 스위치 + 설정에서 붙는 태그 | 켜짐 | 켜짐(같은 프로세스의 모든 프리셋) | 가능(job key 불변) | 아래 1.6의 관문으로 막는다 |

### 1.3 추천안 (가′) 명세(python-expert 구현 요구)
1. **프리셋 인자**: `C2Config.with_10hz_d1(..., imu_residual_median_check: bool = False)`
   - 값은 `c2.py:2964-2969`의 `two_pressure = replace(...)` 한 곳에서만 넣는다. 다른 단계에서 다시 `replace`하지 않는다.
   - 기본 False이므로 프리셋과 클래스 모두 끔이다. LAS-b·K1처럼 "프리셋 기본 켬"으로 바꾸는 것은 판 9 판정 뒤 채택 결정 때 한다.
2. **켜는 수단은 배치에 묶는다**(CLI 자유 플래그를 쓰지 않는다)
   - 판 9 배치 이름 집합(예: `D1_MEDIAN_BATCHES`)을 둔다: `ed9_heldout_v0`, `ed9_heldout_aa2`, `ed9_heldout_aa3`(job 목록은 `heldout_v0_jobs(..., ed8 이름)`과 같음), `ed9_heldout_same_shape`.
     - 판 9가 G′ 처리 팔·T8·사례를 돌리면 `ed9_keys`, `ed9_t8`, `ed9_cases` 등도 넣는다.
   - 이 배치들은 C-m을 켠다. 기존 `ed8_*` 배치는 끔을 유지한다. 그래서 R3a는 `ed8_*`, R3b는 `ed9_*`로 돈다.
   - **현재 커밋 `b3dd2e9a`의 `ed9_heldout_same_shape`는 C-m 없이 돈다.** 이 배치도 켬 집합에 넣어야 한다. 넣지 않으면 A/A 후보 7 job만 끔으로 돌아 짝이 섞인다.
   - `.done`·`<stem>.identity.json`에 배치 이름과 스위치 상태를 남긴다. 판정 도구는 ed9 규칙 집합에서 ed9 배치 이름만 받는다(`jp3_ed8_judge.py:1424-1426` `STAGE5_BATCHES`의 ed9 판).
3. **worker 안에서 설치한다**(spawn)
   - 각 worker가 `with_10hz_d1` 래퍼를 직접 설치한다. 래퍼는 원래 함수를 `imu_residual_median_check=True`로 부른다.
   - 수단(pool initializer 또는 job runtime 키)은 python-expert가 고른다. runtime 키로 하면 `RUNTIME_JOB_KEYS`에 넣어 job key가 바뀌지 않게 한다.
4. **태그는 run 자신의 설정에서 붙인다**
   - `is_d1_median_on(config)`(`config.two_pressure.imu_residual_median_check`), `with_d1_median_tag`, `is_d1_median_tag`를 만든다.
   - `with_switch_tags`의 순서는 LAS → K1 → LSB → TCL → **CM** → ED8이다.
   - 스위치 값이 아니라 설정값에서 태그를 만든다. 그래서 적용이 빠지거나 두 번 되어도 줄에 실제 상태가 남는다.
5. **줄 기록 키(둘째 전달자)**: 예를 들어 `d1_settings: {"imu_residual_median_check": true}`를 켬일 때만 `LINE_RECORD_KEYS`(`run_v5.py:1058-1062`)로 줄에 복사한다. V0 줄에는 지금 제어기 meta가 들어가지 않으므로 태그가 유일한 증거가 된다. 그래서 둘째 전달자를 둔다.
6. **이어 돌리기 검사**: `_check_stored_definition`(`run_v5.py:1010-1024`)에 기대 C-m 상태(배치에서 유도)와 저장 줄의 태그·`d1_settings`가 같은지 비교를 더한다. 다르면 RuntimeError를 낸다.
7. **run 뒤 관문**: `check_d1_median(run_config, expected)`. 그 run이 만든 설정의 `imu_residual_median_check`가 배치 기대값과 다르면 RuntimeError(`check_last_ed8` 꼴)다. V0와 옵션 있는 설정 모두에 적용한다(`verdict_runs.py:871-877`과 `887-894` 두 갈래).

### 1.4 태그 이름(추천)
| 설정 | 판 8까지(끔) | 판 9 배치(켬) |
|---|---|---|
| V0 | `final_C4G2_LAS_K1` | `final_C4G2_LAS_K1_CM` |
| VB(v5 ③) | `final_C4G2_P3_LAS_K1` | `final_C4G2_P3_LAS_K1_CM` |
| VBN, LSN1~4, VBN 민감도, VBKN | `final_C4G2_P3X_LAS_K1_LSB_ED8` | `final_C4G2_P3X_LAS_K1_LSB_CM_ED8` |
| VBN0, VBKN0 | `final_C4G2_LAS_K1_LSB_ED8` | `final_C4G2_LAS_K1_LSB_CM_ED8` |

- 토큰 충돌을 확인했다. `_CM`은 `03_src`·`04_scripts`·`05_tests`의 `*.py`에서 0건이다(Grep count).
- `_CM`을 `_ED8` 앞에 두는 이유: `_ED8`은 "모든 접미사 뒤"라는 계약이 있다(`v5_options.py:60-65`). `with_ed8_tag`(951-956)와 `is_ed8_tag`(997-999)는 꼬리를 해체하지 않고 `endswith`만 본다. `_CM`을 맨 끝에 두면 이 두 함수도 고쳐야 하고, `is_ed8_tag("..._ED8_CM")`가 False가 된다.

### 1.5 판정 도구 영향
| 대상 | 영향 | 필요한 변경 |
|---|---|---|
| `V0_CONTROLLER_TAG`(`jp3_ed8_judge.py:168`, 검사 277-279) | 판 9 V0 줄은 `_CM` 태그라서 ed8 규칙으로는 정체성 결함이 된다 | `RuleSet`에 V0 태그를 넣는다. `ed8`·`ed8_j7a`는 `final_C4G2_LAS_K1`, `ed9`는 `final_C4G2_LAS_K1_CM`. ed9를 저장 C8 줄에 돌리면 정체성 결함(setting_defect)이 나는 것이 맞다. 구현 1차 보고 5절의 ed9 스모크(not_judgeable)는 결과가 바뀐다 |
| `ED8_TAG`·`ED8_P3_OFF_TAG`(130-131, `ed8_identity` 316) | 처리 팔 태그 정체성 | ed9 규칙 집합은 `_CM_ED8` 태그를 쓴다 |
| `V0_ABSENT_KEYS`(171-176) | 새 줄 키 `d1_settings`를 "없어야 할 키"에 넣으면 안 된다 | ed9에서는 `d1_settings`가 있어야 한다(켬 상태 일치) |
| `is_extend_start_tag`·`extend_start_revision_of_tag`·`switch_base_tag`(`v5_options.py:1002-1030`) | `_split_tail`이 `_CM`을 모르면 VBN `..._LSB_CM_ED8`이 `_ED8`만 떼인 채 `..._LSB_CM`에서 멈춘다. 그러면 revision이 None이 되어 ③이 꺼진 것으로 읽힌다. `j_p3_inputs.is_p3_expected`(147)는 설정 이름으로 되돌아가지만, `jp3_j9main_judge.j_p3_rows`(284-297)는 `rule`·`revision` 키를 넣지 못한다. 결과는 J-P3 판정 행 0이다 | `_split_tail`·`_with_tail`에 `_CM` 단계를 넣는다(TCL과 ED8 사이). V0 `final_C4G2_LAS_K1_CM`은 우연히 ③ 끔으로 맞게 읽히지만, 시험은 모든 조합에 대해 둔다 |
| A/A 후보 V0 판별(`aa_pair_verdict`, 1229-1231) | 설정 V0이고 `hydraulic_options`가 None인지만 본다. 스위치 방식이라 바뀌지 않는다 | 조건 줄과 후보 줄이 같은 C-m 상태인지는 `identity_defects`(361-381)가 모든 줄에서 태그로 막는다. ed9 태그만 고치면 된다 |
| 첫 별칭(`stored_cluster_hashes`, 1192-1208) | 저장 격자 V0(C8, 끔) 해시를 켬 조건 줄 해시와 비교한다 | 근거는 R1 스캔 S_격자 = 0과 아래 부분집합 성질이다. 분석적 근거이고 실행 근거는 없다. 규칙 문면에 "격자 V0 해시는 C8 해시를 켬 해시로 쓴다(근거 …)"를 적는다. 실행 근거가 필요하면 확인 필요 2 |
| census V0(`06_analysis/03_hydraulic/coupled/v5/main.jsonl` V0 100줄) | 판 9가 C-J 기준으로 저장 줄을 쓰면 ed9 V0 태그 검사에 걸린다 | 확인 필요 2: 켬으로 100줄 재실행(약 4~5분, 5단계 실측 1356줄/57분 비례) + 저장 줄과 정체성 대조(P9-D1-2, S = 0) |
| `ED8_SETTINGS_EXPECTED`(226-231) | C-m을 `ed8_settings`에 넣으면 키 집합 정확 일치가 깨지고 판이 섞인다 | C-m은 `ed8_settings`에 넣지 않는다 |
| `compare_identity.py`(구현 보고 8절) | 해시·최종 위상·WARN/FAULT 이름만 본다 | 태그 대조를 더한다. 끔은 저장 태그와 같아야 하고, 켬은 저장 태그 + `_CM`이어야 한다 |

부분집합 성질(코드 확인): C-m이 바꿀 수 있는 결정은 C0가 "설명 안 됨"을 낸 경우뿐이다.
- 둘째 비교는 첫 비교가 설명하지 못한 다리에만 적용된다(`two_pressure.py:2131-2136`).
- 설명 안 됨은 곧 `_head_fault(leg, "D1_step")`이다(2024-2025, 2001-2005).
- 이미 범위·전류로 FAULT인 다리는 사유가 `head_faults`에서 오므로 결과가 같다(2025).
- 첫 헤드 FAULT 뒤에는 프리셋의 `suspend_steps_after_head_fault`가 모든 다리의 계단 규칙을 멈춘다(2006-2007, 2072, 1608-1623).
- C-m 상태(`_d1_reference_pairs`)는 출력에 쓰이지 않는다(2151-2167).
- 결론: 저장 끔 줄에 `INFO_HEAD_PRESSURE_FAULT_REASON:<leg>:D1_step`이 없으면 켬 줄의 명령·위상·WARN/FAULT는 같다. 달라지는 것은 INFO 기록과 태그뿐이다.

### 1.6 래퍼와 프리셋이 겹쳐 두 번 적용될 위험
| 경우 | 결과 | 막는 방법 |
|---|---|---|
| C-m 래퍼와 lock window 래퍼(`harness_hydraulics.py:1209-1217`)가 같은 `with_10hz_d1`에 겹쳐 설치된다(VBN) | 둘 다 kwargs를 넘기고, C-m은 원 프리셋 안에서 한 번만 들어간다(1.3-1). 설치 순서와 무관하다. `_LAST_PRESET`도 C-m이 들어간 설정을 잡는다 | C-m 래퍼가 `replace`를 직접 하지 않는다(인자만 넣는다) |
| 같은 worker에 래퍼가 두 번 설치된다 | 불리언이라 값은 같다. 다만 다른 값으로 다시 설치하면 혼동된다 | 표지(`_v5_d1_median`, `_v5_lock_window` 꼴): 같은 값이면 아무것도 하지 않고, 다른 값이면 RuntimeError |
| 호출자가 `imu_residual_median_check=False`를 명시했는데 래퍼가 True로 덮는다 | 조용히 덮인다 | 래퍼는 kwargs에 그 키가 있고 값이 다르면 RuntimeError |
| `with_10hz_d1`을 거치지 않는 설정(피클 복원, `refresh_settings`) | C-m이 조용히 빠진다 | 1.3-7 run 뒤 관문 + 설정에서 붙는 태그 |
| VBN의 ③·LSB·ED8 단계가 `two_pressure`를 다시 만든다 | 해당 없다(모두 `replace`, 1.1 마지막 행) | 시험: VBN 계열 설정 끝 단계에서 C-m 값 유지 |
| 판 9 밖 실행(논문 v5 A형, Chrono, ML)에 C-m이 섞인다 | 배치에 묶여 있어 그 프로세스에는 래퍼가 없다 | 프리셋 기본은 끔으로 유지한다 |

### 1.7 VBN(처리 팔)에도 켜는가
- **켠다. 모든 팔 공통 감시기다.** 판 9 배치 프로세스에서 만드는 모든 프리셋에 적용되므로 VBN, VBN0, LSN1~4, VBN 민감도, VBKN·VBKN0이 함께 켜진다. 각 줄 태그의 `_CM`으로 확인한다.
- 이유
  - A/A 바닥은 V0 + C-m으로 잰다.
  - C-J와 G′는 VBN 대 V0이다. C-m을 한쪽에만 켜면, 가짜 D1 FAULT 제거(판 8 5단계에서 대각 다리를 59.8 s 띄운 기전)가 처리 효과로 섞인다.
  - C-m은 D1″ 센서 진단 안에서만 동작한다(`two_pressure.py` 2035-2036·2103-2108·2139-2167). ED8 변경(PSW, H3′, L-2), LSB, ③과 상태를 공유하지 않는다.
- 판 9 V0의 뜻: "v5 제어기 + C-m"이다. 그래서 `V0_CONTROLLER_TAG` 설명(`jp3_ed8_judge.py:169-170` "기존 설정 그대로")을 판 9 규칙에서 다시 정의해야 한다. 판 9 결과는 "C-m이 없는 v5 제어기"에 그대로 옮겨지지 않는다(논문 v5 서술 주의).
- VBN 쪽 C-m 효과는 봉인 전에 미리 돌려 보면 안 된다(처리 팔 오염). 근거는 단위 시험(18개) + 부분집합 성질 + 줄 태그·관문이다. VBKN(로드 고장 계획)에서 로드 판독이 잔차를 흔드는 경우도 중앙값은 이상값 하나를 견딘다. 다만 이것은 실행 전 예측이 없는 기록 항목이다.

### 1.8 시험 요구(python-expert)
- 태그 함수: `_CM`과 기존 접미사의 모든 조합. 각각 왕복 변환, `switch_base_tag`, `extend_start_revision_of_tag`(4·7·None), `is_ed8_tag`, `is_lock_start_b_tag`를 본다.
- spawn worker 설치: ed9 배치의 V0·VBN 줄은 `_CM` + 설정 켬, ed8 배치는 비트 동일 + 태그 불변.
- 이어 돌리기 거부: 끔 줄이 든 파일로 켬 배치를 이어 돌리면 RuntimeError.
- 래퍼 충돌: 명시 False + 래퍼 True이면 RuntimeError. 다른 값으로 다시 설치하면 RuntimeError.
- 판정 도구: ed9 규칙 집합은 C8 줄을 정체성 결함으로, ed8 규칙 집합은 `_CM` 줄을 정체성 결함으로 본다.

## 2. 질문 2: R3c 진단 job

### 2.1 소유와 경로
| 목록 | 경로(`...\j_p3_cause\ed8_design\stage5_aa_diag\` 아래) | 수 | 만든 스크립트 | 저장된 끔 실행 줄(대조 기준) |
|---|---|---|---|---|
| 진단 1 | `diag_jobs.json`(= `diag2\jobs_gyro.json`, 같은 7 job 확인) | 7 | `scripts\make_diag_jobs.py` | `runs_trace_off.jsonl`, `runs_trace_on.jsonl`(자이로 끔) |
| 경계 훑기 D | `diag2\jobs_sweep.json`(J1shape·J3shape, o 0.0845~0.1005, 0.001 간격 17개씩) | 34 | `diag2\scripts\d2_make_jobs.py` | `diag2\D_sweep_gyro_off_trace_on.jsonl` |
| 경계 훑기 E | `diag2\jobs_sweep_ext.json`(o 0.0745~0.0835, 10개씩) | 20 | `diag2\scripts\d2_make_sweep_ext.py` | `diag2\E_sweep_ext_gyro_off_trace_on.jsonl` |

- 소유: python-expert(provenance의 worktree `ed8-diag`, base `56849248`, `committed: false`, numba 캐시 `python-expert-ed8diag`). 실행기는 `scripts\d1_diag_run.py`, `diag2\scripts\d2_run.py`다.
- `d2_run.py`는 `two_pressure.start_d1_trace()`/`stop_d1_trace()`(73-77행)를 트레이스를 끈 경우에도 부른다. 이 함수는 ed8-diag의 커밋하지 않은 패치(`code\two_pressure.py.patch`)에만 있다. 그래서 C9에서 그대로 돌릴 수 없다.

### 2.2 수 정정과 R3b와의 겹침(`diag_job_census.py`, `diag_vs_keys.py`, 키 파일은 job 정의만 읽음)
| 항목 | 값 |
|---|---|
| 이름(label) | 61 = 7 + 34 + 20 |
| 고유 job | **59**: J1 ≡ J1shape_o0.0875, J3 ≡ J3shape_o0.0875 |
| 5단계 배치(R3b)에도 있는 것 | 5: J1(aa2), J4·S1·S2(ho_v0 aa1), S3(aa2) |
| `ed9_heldout_same_shape` 7 job과 겹침 | 0 |
| R3c에만 있는 것 | 54: J2·J3은 키 파일의 `aa_order[6]`, 나머지는 훑기 52 |

### 2.3 실행 요구
- 끔 실행(트레이스 없음)은 R3a와 같은 방식이고, 켬 실행은 1.3의 스위치를 쓴다. 둘 다 C9 코드에서 돈다.
- 트레이스 켬 실행은 다음 순서다.
  1. C9 위에 진단 worktree를 따로 만든다(잠긴 C9 worktree에는 쓰지 않는다).
  2. trace 패치를 옮긴다.
  3. trace 행에 C-m 필드를 더한다: `median_change_N`, 유효 기준 수, 분기(`imu_residual` / `imu_residual_median` / 설명 안 됨).
- C-m 코드가 원 패치와 같은 영역(`two_pressure.py` 2005~2113)을 고쳤으므로 패치를 그대로 적용하면 충돌할 수 있다. 옮기는 일은 python-expert 몫이다.
- 하네스 기본 자이로는 끔이다. B·C(자이로 공급) 변형은 J7 B 쪽 진단이라 선택(기록) 항목이다.
- 예상 시간: 고유 59 job, 4 worker, 트레이스 켬 기준 약 10~15분(진단 1 실측 job당 18~53 s, provenance `run_log.runs`).

### 2.4 기대값(C-m 켬, 자이로 끔; 근거 `control_d1_rule\false_fault_rows.csv`)
| 묶음 | job | 기대 | 판정·기록 |
|---|---|---|---|
| C0에서 D1_step FAULT가 난 job | 고유 9개: J1(=J1shape .0875), J4, S1, J1shape o 0.0835·0.0845·0.0855·0.0865·0.0885·0.0895 | 저장 결정 주기(J1·J1shape t 24.9 s, S1 24.8 s, J4 45.0 s)에 `INFO_HEAD_PRESSURE_FAULT_REASON:*:D1_step`이 없다. 그 주기에 `INFO_PRESSURE_STEP:<leg>:head:imu_residual_median`이 생긴다. 다리: J1 FL·RR, J1shape .0865 FL·RR, J4 RR, S1 RL, 그 밖은 RR. 둘째 비 `dmed/θ` 예측: J1 0.038/0.056, J4 0.078, S1 0.041, 훑기 0.035~0.0645, .0835 0.040. 최대 0.078 | 사유 변화는 판정(정확). 결정 뒤 궤적(최종 위상 ready 예상, 새 FAULT 없음)은 기록이다. 새 FAULT나 비 ready가 나오면 보고하되 멈추지 않는다 |
| 나머지 | 50개(J2, J3, S2, S3, J3shape 전부, FAULT 없던 J1shape) | 저장 끔 줄과 `commands_sha256`·`final_phase`·WARN/FAULT 이름 집합이 비트 동일하다. `imu_residual_median` INFO는 0이다 | 판정(정확). 다르면 구현과 규칙의 불일치이므로 멈춘다 |
| 끔 실행(C9, 스위치 끔) | 59개 | 저장 진단 줄과 비트 동일하다(C8 → T8⁗ 사이 실행 경로 불변은 `test_working_tree_changes_since_c8_stay_off_the_run_path`, 트레이스 켬·끔 재현은 `repro_check.csv`) | 판정(정확) |
| 자이로 공급 B·C(선택) | 7 + 7 | 같은 9개 중 진단 1의 3개(J1, J4, S1)가 설명된다. 둘째 비 ≤ 0.173(S1 RL) | 기록 |

- 기준 유효성의 위험: 결정 주기 바로 앞 세 주기(j−1..j−3) 가운데 하나라도 재접촉 의심 등으로 `is_crawler_lifted`가 False가 되면 기준이 비워진다. 그러면 C0만 쓰고 FAULT가 남는다.
  - 내 재생(`d1_rule_eval.py:107-113`)은 trace의 `is_crawler_lifted`·f_z로 같은 조건을 썼다. 그러나 구현 경로로는 처음 보는 것이다.
  - 9개 중 하나라도 FAULT가 남으면 예측 실패다. 원인(기준 리셋인지 다른 것인지)을 trace로 보고 멈춘다.
- R3b와 겹치는 J1·J4·S1의 켬 결과는 R3b 줄과도 같아야 한다(같은 job, 같은 C9, 같은 스위치). 교차 확인용이다.
- 출력: `ed9_design\d1_prerun\r3c_diag_<C9>\`(구현 1차 보고 9절과 같다).

## 3. 질문 3: R2 대 P9-D1-6
| 도약 | 과도 후보 n | C0 | C-m | 잃은 건수(C0 − C-m) | 손실 %p | 한쪽 95 % CP 상한 %p | C-m − D1′ %p |
|---|---|---|---|---|---|---|---|
| −150 bar | 1004 | 1004 | 1003 | 1 | 0.10 | 0.47 | +1.20 |
| −100 bar | 537 | 527 | 524 | 3 | 0.56 | 1.44 | +4.10 |
| +100 bar | 582 | 560 | 556 | 4 | 0.69 | 1.57 | +2.41 |
| +150 bar | 1011 | 1011 | 1011 | 0 | 0 | 0.30 | +1.78 |

(`ml_inject_cm.csv` sha `48a8e4c2…`, 계산 `r2_loss_cp.py`, dynamics-dev, scipy `beta.ppf`. 연속/이산: 10 Hz 순간 표본 기록 재생, $T$ = 0.1 s, 개루프)

의견
1. **충족한다(보수적 해석).** P9-D1-6은 "k1 밖" 손실을 묻는다. C-m은 C0의 부분집합(`two_pressure.py:2131-2136`)이라 손실은 잃은 건수일 뿐이고 상쇄되는 이득이 없다. 그러니 k1까지 포함한 전체 손실이 이미 상한이다. 점추정 ≤ 0.69 %p, CP95 상한 ≤ 1.57 %p로 모두 3 %p 아래다.
2. **다만 정의대로는 아직 대조하지 않았다.**
   - R2는 구간(k1 / k2 / late)을 나누지 않았다.
   - "k1 밖" 손실은 잃은 건수 ÷ k1 밖 후보 수다. 최악(잃은 것이 모두 k1 밖)에도 k1 밖 후보가 34 / 100 / 134 / 0개 이상이면 3 %p 아래다.
   - 과도 구간이 크롤러 이탈 뒤 최대 2.5 s(약 25주기)라서 이 조건은 거의 확실하다. 하지만 수치로 확인하지는 않았다.
   - 대조하려면 R2 스크립트에 사건 기준 구간 열을 더해야 한다(ML에는 패드 들림 사건이 없으므로 기준 시각 정의가 먼저 필요하다. 확인 필요 4).
3. **독립성 가정**: 주입은 192 에피소드 안에서 서로 상관된다. 그래서 CP 상한은 낙관적이다. 에피소드 단위 bootstrap은 stats 몫이다. 잃은 건수가 1~4라서 결론이 뒤집힐 가능성은 작다고 본다(판단, 계산하지 않음).
4. **모집단 차이**: 하네스는 +100 bar 전체 손실이 4.8 %p였다(88.4 → 83.6 %, k1 82.7 → 20.5 %가 대부분). ML은 0.69 %p다. 하네스의 k1 손실은 시각 몫(순간 압력 대 IMU 10 ms 평균)에 기댄 검출이다(이전 보고 2.3). ML 과도 구간은 크롤러 이탈 과도이고 패드 들림 사건이 없어 이 꼴이 드물다. 그래서 P9-D1-6을 "전체 주기"로 바꾸면 하네스에서는 실패하고 ML에서는 통과한다. 정의는 "k1 밖"으로 두고, k1 손실은 따로 기록하기를 권한다.
5. **문턱 3 %p의 성격**: 안전에서 나온 한계가 아니다. 하네스 최대 2.41 %p에 여유를 둔 기록 기준이다. 놓친 도약은 다음 주기의 D1 범위·고착·전류와 F1이 받친다(명세 219.2 (d) 끝). 그래서 판정 항목으로 올릴지와 허용폭은 stats가 정한다. 내 초안에서는 "기록"이다.
6. P9-D1-5(C-m ≥ D1′, 행마다)는 모든 과도 행에서 충족하고, 조용한 주기는 100 %다. 실제 도약(주입 없음)의 거짓 FAULT는 D1′ 3, C0 0, C-m 0이다.

## 4. 이전 보고(`control_d1_rule\report.md`, decision_log 인용 sha `a5bdeffc…`) 정오
| 위치 | 이전 | 정정 | 근거 |
|---|---|---|---|
| 0절 C-m 항목, 2.2 표 C-d 행, 4.1 P9-D1-3 | 둘째 비 최대 0.065(자이로 없음) | **0.078**(J4 RR, 진단 1, 자이로 없음). 자이로 공급 최대 0.173은 그대로 | `false_fault_rows.csv` 4행 `dmed_over_thr` 0.078, `is_lever_missing` True |
| 0절 "진단 trace 75개(고유 job 61개)" | 고유 job 61 | 이름 61, 고유 job 59(trace 75 = 7 + 7 + 7 + 34 + 20) | 2.2 |

- 판정 결론은 바뀌지 않는다(여유가 1/0.078 ≈ 13배).
- 봉인 문서가 이 수를 인용하면 정정된 값을 쓴다. 원 보고 파일은 sha로 인용되므로 고치지 않았다.

## 5. 가정
| 가정 | 값 | 근거 |
|---|---|---|
| R3c 예상 시간 | 10~15분 | 진단 1 실측 job당 18~53 s, 4 worker |
| census 100줄 재실행 시간 | 4~5분 | 5단계 1356줄 57분 비례(같은 worker·마스크) |
| ML k1 밖 후보 수 | 손실 대조에 충분 | 과도 구간 길이(약 25주기). 확인하지 않음 |
| 태그 토큰 | `_CM` | 코드 Grep 0건. 문서·결과 파일의 토큰은 보지 않음 |

## 6. 확인 필요(사용자)
1. 스위치 경로 (가′)(배치에 묶인 스위치 + 설정에서 붙는 태그 `_CM`, `_ED8` 앞)를 채택할지. 대안은 CLI 플래그(`--d1-median on|off` 필수)인데, 운영자 실수 여지가 더 크다.
2. 저장 census V0(100줄)와 저장 격자 V0(768 run, 첫 별칭 해시)를 판 9에서 그대로 쓸지.
   - 권고: census V0 100줄은 켬으로 재실행(약 5분)하고 저장 줄과 정체성 대조한다(P9-D1-2, S = 0 예측).
   - 격자 해시는 분석적 근거(부분집합 성질 + R1 S = 0)로 쓰고 규칙에 적는다.
   - 격자를 다시 돌리려면 저장 때의 실행기 경로가 같은지 python-expert 확인이 먼저다.
3. 판 9 V0 = "v5 제어기 + C-m"으로 다시 정의하는 것과, 이 때문에 판 9 결과를 논문 v5(C-m 없음)에 그대로 옮기지 않는다는 점.
4. P9-D1-6의 ML 쪽 구간 기준 시각(크롤러 이탈 시각 등)과, 그것을 판정으로 둘지 기록으로 둘지(stats와 함께).

## 7. 위임 필요
- **python-expert**: 1.3 구현 전체
  - 프리셋 인자, 배치 집합(`ed9_heldout_same_shape` 포함), worker 설치, 태그 함수(`_split_tail`·`_with_tail`·`with_switch_tags`), `d1_settings` 줄 키, 이어 돌리기 검사, run 뒤 관문
  - 1.8 시험
  - 판정 도구 ed9 규칙 집합의 태그(V0·처리 팔), ed9 `STAGE5_BATCHES`
  - `compare_identity.py` 태그 대조
  - R3c용 trace 패치를 C9로 옮기기와 C-m 필드 추가
  - R2 구간 열
  - 제어기 meta 전체를 같다고 비교하는 곳이 있는지 Grep. C-m 켬이면 `two_pressure` meta에 키가 하나 늘어난다(`two_pressure.py:931-932`)
- **stats-design-expert**: P9-D1-6 허용폭과 판정·기록 여부, R2 에피소드 군집 반영, census V0 재실행 여부가 A/A·C-J 표본에 미치는 영향
- **verif-protocol-auditor**(봉인 전)
  - 접미사 조합 누락(`_CM` × `_P3*`, `_LSB`, `_ED8`)
  - 래퍼와 프리셋 이중 적용 관문
  - 배치와 스위치의 대응(`.done`·identity.json)
  - ed8 규칙 집합 스모크 결과 불변

## 8. 수행한 작업과 공개(실제 행위)
- **실행**(dynamics-dev `conda run -n dynamics-dev python -I -B`, PowerShell)
  - `...\scratchpad\control-ed9switch\diag_job_census.py <stage5_aa_diag>`: 이름·고유 job·중복만 출력
  - `...\scratchpad\control-ed9switch\diag_vs_keys.py <stage5_aa_diag> <keys_seal_41e107e9\heldout_g_ed8.json>`: 키 파일의 job 정의만 읽고 이름·배치 이름만 출력
  - `...\scratchpad\control-ed9switch\r2_loss_cp.py <d1_prerun\ml_inject_cm.csv>`
  - depcheck(control-expert): 모든 항목 OK
- **Read**
  - `d1_prerun\impl_report.md` 전체, `control_d1_rule\report.md` 전체, decision_log 833~836행
  - ed9-impl의 `c2.py` 2830~3088, `v5_options.py` 20~109·780~1139, `jp3_ed8_judge.py` 100~339·355~394·1185~1444, `jp3_ed7_judge.py` 380~419, `j_p3_inputs.py` 140~159, `jp3_j9main_judge.py` 275~299, `run_v5.py` 100~329·440~569·805~1104, `verdict_runs.py` 330~449·800~894, `harness_hydraulics.py` 1185~1254, `two_pressure.py` 1990~2189(일부 Grep 문맥 포함)
  - `stage5_aa_diag\diag_jobs.json`, `provenance.json` 1~80, `diag2\jobs_sweep.json` 1~60
  - `control_d1_rule\false_fault_rows.csv`, `rule_eval_summary.json` 1~28
  - `d1_prerun\ml_inject_cm.csv`, `ml_inject_cm.provenance.json`
- **Grep**
  - ed9-impl의 `03_src\outrigger_sim\control`·`hydraulics`, `04_scripts` 코드(`*.py` 한정): 함수·태그·설정 이름
  - `05_tests`·`03_src`·`04_scripts`의 `_CM` 건수
  - `stage5_aa_diag\code\two_pressure.py.patch`, `diag2\scripts\d2_run.py`, `diag2\jobs_*.json`(label 건수), `control_d1_rule\scripts\d1_rule_eval.py`
- **Glob**: `stage5_aa_diag`, `stage5_aa_diag\diag2`
- **열지 않은 것**: `j9_runs\` 아래 전부(진단 job 파일의 `stored` 칸에 저장 줄의 해시·위상이 적혀 있는 것은 diag_jobs.json을 읽으며 보았다), `d1_prerun\judge_smoke_320a1f64\`, `scan_d1_step.json`, P8-2 경로 2 자료, `stage5_aa_cause\`
- **쓰기**: scratchpad `control-ed9switch\`에만 스크립트 3개를 썼다. 프로젝트 파일은 쓰지 않았고 코드도 고치지 않았다.
- Bash, 파이프, heredoc을 쓰지 않았다. 프로세스를 종료하지 않았다. 병렬 실행을 하지 않았다. Julia 교차 검증은 하지 않았다(선형 루프·리카티 계산이 없는 코드 경로 검토와 계수 재계산이다).
- 의존성 점검: CHECKED, 모두 OK(control 0.10.2 등, julia·control-julia Manifest 있음).

사용한 스킬: 없음
