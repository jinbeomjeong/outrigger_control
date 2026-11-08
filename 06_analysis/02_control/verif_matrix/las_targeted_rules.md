# LAS-b(이륙 접근 감속) 하네스 표적·채택 규칙

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `las_targeted_rules.sha256`에 있다. 이 파일은 더 고치지 않는다. 고칠 일이 생기면 덧붙임 판(`las_targeted_rules_rev1.md`)을 새로 봉인한다.
> - **표적 실행 전에 봉인한다.** 지금까지 본 것은 진단 20건뿐이다(control-expert scratchpad `ctrl_liftoff\runs\*.json`, 래퍼 LAS-a·수정 A·I6 등). LAS-b 결과는 아직 없다.
> - 사용자 결정(2026-11-08):
>   - 수정 방향은 LAS-b다.
>   - 진행은 표적 → 채택 기준을 충족하면 구현·명세 개정·그림자 판정·작동 행 재실행까지 자동, 미달이면 멈추고 질문한다.
>   - S1·J2(Q-C, 명세 424.9.3.1)는 현행을 유지한다.
>   - A-3(단단한 균일 지면 해시 불변)을 유지한다.
> - 근거 설계: control-expert `liftoff_fix_design.md`(scratchpad `ctrl_liftoff`). 원인은 P30fz 무효(크롤러 구역 규칙이 최소 다리를 0으로 올린 뒤 heave 빼기가 0)와 자세 포화 속도로 크롤러를 뗀 것이다.

기준 제어기: `final_C4G2_P3`(master 38d08ab). 하네스 기준 기록: `06_analysis/03_hydraulic/coupled/v5/d1.jsonl`(V0 = 태그 없음, VB = `final_C4G2_P3`). 제어 주기 $T_s$ = 0.1 s, 출력 지연 d = 1. 힘은 실린더 순 힘 [N], $F_{min}$ = 9,414.589 N.

## 1. 후보 정의

### 1.1 기호

| 기호 | 뜻 | 단위 |
|---|---|---|
| $u_k$ | 주기 $k$에서 `_apply_pre_loc_lift_pause` 직후의 다리 속도 명령(FL, FR, RL, RR) | m/s |
| $\bar u_k$ | $u_k$의 산술 평균 | m/s |
| $\hat L_{i,k}$ | `self._load_estimate_N(reading.cylinder_force_lower_N)`의 다리 $i$ 값 | N |
| $W_{ref}$ | `self._reference_weight_N()` | N |
| $v_{max}$ | `self.geometry.max_speed_m_s` | m/s |

### 1.2 LAS-b (기본값 = 변형 `b0`)

**적용 위치**: `C2Controller._level_step`에서 `leg_speeds = self._apply_pre_loc_lift_pause(reading, leg_speeds)` 바로 다음, `_is_diff_sink_holding()` 덧셈 앞.

**상태**: `armed`(아직 한 번도 시작하지 않음, 초기 참), `active`(거짓), `t_start`, `sum_count`(0).

**시작**: `armed`이고 아래 S1~S8이 모두 참인 주기에 `active ← 참`, `armed ← 거짓`, `t_start ← t_k`, 사건 `INFO_LIFTOFF_SLOW:<argmin_i L̂ 다리 이름>`을 낸다. 시작은 실행당 한 번이다.

| # | 조건 |
|---|---|
| S1 | `config.soil.enable` |
| S2 | `_state.phase is C2Phase.LEVEL` |
| S3 | 이 실행에서 LOC(`crawler_liftoff_confirmed`)가 한 번도 없었다(LOC 취소 뒤에도 거짓) |
| S4 | 토양 모드가 시작되지 않았다(`_has_soil_mode_started()` 거짓) |
| S5 | `_state.in_crawler_zone` |
| S6 | 재접근 중인 다리가 없다(`_reapproaching_legs().any()` 거짓, 이 주기 `_level_step`이 계산한 값) |
| S7 | $\sum_i \hat L_{i,k} \ge \alpha\, W_{ref}$ 이고 $\min_i \hat L_{i,k} < \beta\, F_{min}$ |
| S8 | $\bar u_k > \gamma\, v_{max}$ |

**작용**(`active`인 주기, 시작 주기 포함): 끝 조건을 먼저 본다. 끝나지 않았으면 $u_k \leftarrow u_k \cdot (\gamma v_{max} / \bar u_k)$를 적용한다. 단 $\bar u_k \le \gamma v_{max}$이면 그대로 둔다.

**끝**(`active`인 주기에서 작용 전에 본다; 참이면 `active ← 거짓`, 사건 `INFO_LIFTOFF_SLOW_END:<사유>`, 그 주기는 작용하지 않음; 다시 시작하지 않음):

| 사유 | 조건 |
|---|---|
| `loc` | S3 거짓 |
| `phase` | S2 거짓 |
| `soil` | S4 거짓 |
| `reapproach` | S6 거짓 |
| `sum` | $\sum_i \hat L_{i,k} \ge \alpha_{end} W_{ref}$인 주기가 연속 $n_{end}$번(이 주기 포함)에 이르렀다. 카운터는 `active` 동안만 세고, 조건이 거짓인 주기에 0으로 돌아간다 |
| `time` | $t_k - t_{start} \ge T_{max} - 10^{-9}$ s |

### 1.3 변형과 비교 후보

| 이름 | α | β | γ | α_end | n_end | T_max [s] |
|---|---|---|---|---|---|---|
| **b0**(기본) | 0.6 | 3.5 | 0.16 | 0.85 | 5 | 1.5 |
| b-a5 | **0.5** | 3.5 | 0.16 | 0.85 | 5 | 1.5 |
| b-a7 | **0.7** | 3.5 | 0.16 | 0.85 | 5 | 1.5 |
| b-T10 | 0.6 | 3.5 | 0.16 | 0.85 | 5 | **1.0** |
| b-T20 | 0.6 | 3.5 | 0.16 | 0.85 | 5 | **2.0** |
| **LAS-a**(비교 전용) | 0.6 | 없음(S7 둘째 조건 없음) | 0.16 | 없음 | 없음 | 없음(S3·S2만으로 끝) | 

LAS-a의 정의:
- S4·S6·`armed` 단발 없이, S1·S2·S3·S5·S7(합 조건만)·S8이 참인 **매 주기** 작용한다.
- 여기에 P30fz `_slow_lift`의 보완(heave 빼기와 평균 올림 뒤에도 평균 > 0.16 $v_{max}$면 비례로 0.16 $v_{max}$까지 축소)을 더한다.
- 진단 래퍼 `probe.py` 개입 `approach`와 같다.
- LAS-a는 T-1에서 비교 기록만 남긴다. 채택 후보가 아니다(3.3절).

## 2. 실행 목록

- 키 형식은 `<d1 row_key>|<setting>|e<eps>`이고, `d1_rows.jobs()`의 `d1.key`와 같다. setting은 V0·VB, eps는 0·0.002다.
- 기준 해시는 `v5/d1.jsonl`의 같은 키 `commands_sha256`이다(부록 A·B에 앞 12자).

| 묶음 | 내용 | 후보 | 실행 수 |
|---|---|---|---|
| T-0 기준 재현 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|V0\|e0`, `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|VB\|e0` | `current`(래퍼 장착, 후보 끔) | 2 |
| T-1 | 부록 A 8키(이 계열) | b0, b-a5, b-a7, b-T10, b-T20, LAS-a | 48 |
| T-2 | 부록 B 184키: H-R-A 나머지 136(행 34 × 4), H-R-0 상단 roll+op·roll+val·roll-op·roll-val·diag-op·diag-val × K1·K3(행 12 × 4 = 48) | 3.1절에서 고른 변형 하나 | 184 |
| T-2′(조건부) | T-2 묶음 그대로 | 3.2절 차순위 변형 하나 | ≤ 184 |

비용 추정(4 동시 실측): VB 약 105 s/건, V0 약 41 s/건. 묶음 안에서 VB·V0는 반반이다.

## 3. 채택 기준과 선택 규칙

### 3.1 채택 기준 6개(한 변형에 대해 T-1 + T-2 전부)

| # | 기준 | 정의 |
|---|---|---|
| C1 | 계열 회복 | T-1 8키 모두 `d1.verdict` = pass이고, `F_judged_min_N` ≥ $F_{min}$ + 1,000 N(= 10,414.589 N) |
| C2 | 나빠짐 0 | T-1·T-2 모든 키에서 기준 pass → fail 0, 기준 allowed_stop → fail 0. 기준 fail 키는 `fail_items`에 새 항목이 생기지 않는다(집합 포함 관계) |
| C3 | 새 FAULT 0 | 기준 기록에 없던 `FAULT*` 사건 이름이 생기지 않는다(`event_names`의 FAULT 접두 이름 집합 비교) |
| C4 | LOC 지연 | G6-2 항목(r72 판정기 자체 `t_off`·`T_lim` 2.9 s, 조건 6 포함)이 기준 pass인 키에서 pass를 유지한다. T-1 8키는 판정기의 LOC − $t_{off}$ ≤ 2.9 s 값을 표로 낸다 |
| C5 | 시간·행정 | 규칙이 작동한(시작 사건이 있는) 키에서 `t_ready_s` 증가 ≤ 5.0 s, `stroke_max_m` 증가 ≤ 0.001 m(기준 대비) |
| C6 | A-3 | T-2의 H-R-0 48키에서 `commands_sha256` = 기준 해시(규칙 미작동). 그림자 판정(4절)의 강체 균일·G1 균일 기록도 미작동 |

### 3.2 변형 선택 순위(T-1 결과만으로 정한 뒤 T-2)

1. T-1에서 C1·C2·C3·C4·C5를 모두 만족한 LAS-b 변형만 후보다(C6은 T-2에서 본다).
2. 후보 가운데 T-1 8키의 $\min_{\text{키}}$ `F_judged_min_N`이 가장 큰 변형을 1순위로 둔다. 그 값과의 차가 500 N 안이면 동률로 본다.
3. 동률 안에서는 다음 순서로 정한다.
   1. T-1 8키 LOC − $t_{off}$ 최대값이 작은 것
   2. T-1 8키 `t_ready_s` 증가 최대값이 작은 것
   3. b0에 가까운 것(b0 > b-T20 > b-T10 > b-a7 > b-a5 순)
4. 1순위 변형으로 T-2를 돌린다. C2·C3·C4·C5·C6를 모두 만족하면 **채택**이다.
5. 1순위가 T-2에서 실패하면, 실패 키가 C6 **아닌** 기준에서만 나왔을 때 한해 3번 순서의 차순위 변형 하나로 T-2′를 돌린다. T-2′도 실패하면 멈춘다.

### 3.3 LAS-a로 물러나는 조건

- LAS-a로는 **자동으로 물러나지 않는다.**
- LAS-b 변형이 하나도 후보가 되지 못하면 멈추고 사용자에게 묻는다(5절 H-3). 이때 T-1 LAS-a 결과(C1·C4·C5)를 함께 낸다.
- LAS-a는 S7 둘째 조건이 없어 토양 대응 실행 대부분에서 작동하므로 C6(A-3) 위반이 예상된다. 그래서 사용자 결정 없이 쓰지 않는다.

## 4. T4h 그림자 판정(채택 뒤, 재실행 범위 결정)

**목적**: 저장 실행 각각에 대해 "채택 변형의 시작 관문이 한 번이라도 섰는가"를 재실행 없이 정한다.
- 규칙은 시작 전까지 명령을 바꾸지 않는다. 따라서 미작동 = 명령 비트 동일 = 결과 재사용이다.
- 작동 = 재실행 대상이다.

**입력**: T4h npz(`t_s`, `phase`, `lower_estimate_N`, `command_m_s`, `meta_json` 사건 목록과 설정). 실행 설정(soil.enable, $W_{ref}$, $F_{min}$, $v_{max}$)은 `meta_json` 또는 같은 코드의 프리셋·YAML에서 얻는다.

**판정**: 주기 $k$마다 S1~S7을 기록값으로 평가하고, 모두 참인 첫 주기가 있으면 "작동"이다.
- S8은 기록 명령이 P30fz 단계 값이 아니므로 **참으로 둔다**(보수 쪽: 작동을 넘치게 셀 수는 있어도 놓치지 않는다).
- S5(크롤러 구역)는 기록에 없다. python-expert가 코드로 "토양 대응 실행에서 LOC 전 LEVEL이면 `in_crawler_zone` = 참"임을 보이면 참으로 둔다. 보이지 못하면 S5를 참으로 둔다(보수 쪽).
- S3·S4·S6은 사건(`crawler_liftoff_confirmed`, `soil_mode_start`, `leg_reapproach_start`/`leg_reapproach_contact`)의 시각으로 정한다. 같은 시각 사건은 그 주기 `_level_step` 안의 순서와 맞춘다. python-expert가 순서를 코드에서 확인해 도구에 적는다.
- `lower_estimate_N`이 $\hat L$(1.1절)과 같은 양인지 python-expert가 코드로 확인한다. 다르면 그 기록은 "판정 불가 → 재실행"이다.
- 필요한 필드가 하나라도 없으면 "판정 불가 → 재실행"이다.

**도구 검증**(그림자 결과를 쓰기 전에 통과해야 한다):
- V-1: 실제 계측 실행(래퍼 장착, 관문 평가만) 10건 이상과 비교한다. 작동 3건 이상, 미작동 3건 이상, VB·V0 포함. 첫 작동 주기의 시각이 오프라인과 같아야 한다. 미작동 기록은 오프라인도 미작동이어야 한다.
- V-2: 미작동으로 판정한 기록 3건을 채택 구현으로 재실행해 `commands_sha256` = 저장값임을 확인한다.

**T4h가 없는 기록**(V0 등): 그림자 실행(관문 평가만, 작용 없음)이나 채택 구현 재실행으로 정한다. 비용은 원 실행과 같다.

**대상**: `v5/` 아래 결과(d1·main·pressure_only·overlap·item8·u9_targeted·dg3·noise_vb·seedext 등), U-3·U-6, D-1 Chrono 행(Chrono 주기 기록에 같은 필드가 있으면 같은 판정, 없으면 해당 행 재실행).

## 5. 관문(멈춤 조건)

| # | 조건 | 처리 |
|---|---|---|
| H-1 | T-0 재현 해시 ≠ 기준 해시 | 멈춤(래퍼·코드 차이 진단) |
| H-2 | 래퍼 실행 오류(`error` 줄) 1건 이상 | 그 키를 1회 재시도. 다시 실패하면 멈춤 |
| H-3 | 3.2절 1번 후보 0개 | 멈추고 질문(LAS-a 결과 첨부) |
| H-4 | 채택 변형이 T-2(·T-2′)에서 실패, 또는 C6 위반 | 멈추고 질문 |
| H-5 | 그림자 도구 검증 V-1·V-2 실패 | 멈추고 질문(전수 재실행 비용 제시) |
| H-6 | 구현 비트 동일 시험(6절) 실패 | 멈춤(구현 결함, python-expert 수정 뒤 재시험) |
| H-7 | 작동 행 재실행에서 C2·C3 위반이 하나라도 | 멈추고 질문 |

관문을 모두 지나면 다음은 자동이다(사용자 결정): 03_src 구현 → 비트 동일 시험 → 명세 개정 → 그림자 판정 → 작동 행 재실행 → 판정. 커밋은 프로젝트 규칙(integrity-checker 먼저)을 따른다.

## 6. 구현 비트 동일 시험(03_src 반영 뒤)

| # | 시험 | 기준 |
|---|---|---|
| B-1 | `liftoff_approach_slow.enable = False`(클래스 기본)로 T-0 2키와 기존 해시 고정 단위 시험 | 해시 = 기준(현행과 비트 동일) |
| B-2 | 채택 변형을 켠 프리셋으로 T-1 8키 | 해시 = 같은 변형의 래퍼 T-1 해시 |
| B-3 | 같은 프리셋으로 T-2에서 작동한 키 10건 이상(없으면 전부)과 미작동 키 10건 | 작동 키 해시 = 래퍼 T-2 해시, 미작동 키 해시 = 기준 해시 |

## 부록 A. T-1 키(8)

| 키 | 기준 판정 | 기준 F_judged_min [kN] | 기준 해시(앞 12자) |
|---|---|---|---|
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|V0\|e0` | pass | 9.681 | a5c909840fbd |
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|V0\|e0.002` | fail | 9.354 | 4b571f0b1e67 |
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|VB\|e0` | fail | 9.103 | 71b0f607e312 |
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|VB\|e0.002` | fail | 8.760 | db30c50d976f |
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|V0\|e0` | fail | 5.290 | e46d74a1cb4a |
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|V0\|e0.002` | fail | 5.314 | 31e7f3d26fd6 |
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|VB\|e0` | fail | 4.947 | ab995e0ad0ff |
| `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|VB\|e0.002` | fail | 4.738 | f58ed449ec86 |

## 부록 B. T-2 키(184)

| 키 | 기준 판정 | 기준 F_judged_min [kN] | 기준 해시(앞 12자) |
|---|---|---|---|
| `D1\|H-R-0\|rigid\|T\|diag-op\|K1\|V0\|e0` | pass | 54.084 | 46e7b1296ca5 |
| `D1\|H-R-0\|rigid\|T\|diag-op\|K1\|V0\|e0.002` | pass | 53.873 | 2132cd63a94d |
| `D1\|H-R-0\|rigid\|T\|diag-op\|K1\|VB\|e0` | pass | 53.906 | 904ad9c6c52d |
| `D1\|H-R-0\|rigid\|T\|diag-op\|K1\|VB\|e0.002` | pass | 53.830 | 3277e0f03df8 |
| `D1\|H-R-0\|rigid\|T\|diag-op\|K3\|V0\|e0` | pass | 52.369 | ff75943e3069 |
| `D1\|H-R-0\|rigid\|T\|diag-op\|K3\|V0\|e0.002` | pass | 51.797 | 29647da440e3 |
| `D1\|H-R-0\|rigid\|T\|diag-op\|K3\|VB\|e0` | pass | 53.024 | a5d4a28a1326 |
| `D1\|H-R-0\|rigid\|T\|diag-op\|K3\|VB\|e0.002` | pass | 53.608 | 7d587d1fe3f4 |
| `D1\|H-R-0\|rigid\|T\|diag-val\|K1\|V0\|e0` | pass | 54.042 | 48114616d0a4 |
| `D1\|H-R-0\|rigid\|T\|diag-val\|K1\|V0\|e0.002` | pass | 54.210 | b8c84f2ed2d6 |
| `D1\|H-R-0\|rigid\|T\|diag-val\|K1\|VB\|e0` | pass | 53.641 | 4442cbf39584 |
| `D1\|H-R-0\|rigid\|T\|diag-val\|K1\|VB\|e0.002` | pass | 53.757 | 9e3bb5ec2892 |
| `D1\|H-R-0\|rigid\|T\|diag-val\|K3\|V0\|e0` | pass | 51.647 | a4795c1dbc5f |
| `D1\|H-R-0\|rigid\|T\|diag-val\|K3\|V0\|e0.002` | pass | 50.677 | e61694ef8c98 |
| `D1\|H-R-0\|rigid\|T\|diag-val\|K3\|VB\|e0` | pass | 50.637 | d09ecd5e3902 |
| `D1\|H-R-0\|rigid\|T\|diag-val\|K3\|VB\|e0.002` | pass | 51.432 | 62092e69be92 |
| `D1\|H-R-0\|rigid\|T\|roll+op\|K1\|V0\|e0` | pass | 54.829 | 76868d9a73bb |
| `D1\|H-R-0\|rigid\|T\|roll+op\|K1\|V0\|e0.002` | pass | 54.427 | a1e1b5a0e331 |
| `D1\|H-R-0\|rigid\|T\|roll+op\|K1\|VB\|e0` | pass | 53.825 | 9bc9bc9dbf40 |
| `D1\|H-R-0\|rigid\|T\|roll+op\|K1\|VB\|e0.002` | pass | 53.844 | 95fa3f64e227 |
| `D1\|H-R-0\|rigid\|T\|roll+op\|K3\|V0\|e0` | pass | 53.325 | 519fca0abe75 |
| `D1\|H-R-0\|rigid\|T\|roll+op\|K3\|V0\|e0.002` | pass | 54.922 | 7bce0cdbe132 |
| `D1\|H-R-0\|rigid\|T\|roll+op\|K3\|VB\|e0` | pass | 53.064 | ac2323e059b8 |
| `D1\|H-R-0\|rigid\|T\|roll+op\|K3\|VB\|e0.002` | pass | 53.529 | 2fa92137b9ae |
| `D1\|H-R-0\|rigid\|T\|roll+val\|K1\|V0\|e0` | pass | 54.156 | 8f055ad8bc14 |
| `D1\|H-R-0\|rigid\|T\|roll+val\|K1\|V0\|e0.002` | pass | 53.707 | 734c12f878c9 |
| `D1\|H-R-0\|rigid\|T\|roll+val\|K1\|VB\|e0` | pass | 52.363 | 37bf35d552db |
| `D1\|H-R-0\|rigid\|T\|roll+val\|K1\|VB\|e0.002` | pass | 53.187 | 18ae05aa7591 |
| `D1\|H-R-0\|rigid\|T\|roll+val\|K3\|V0\|e0` | pass | 48.231 | 4091870ab120 |
| `D1\|H-R-0\|rigid\|T\|roll+val\|K3\|V0\|e0.002` | pass | 48.923 | a67d9380a497 |
| `D1\|H-R-0\|rigid\|T\|roll+val\|K3\|VB\|e0` | pass | 48.891 | 41bed8e8015d |
| `D1\|H-R-0\|rigid\|T\|roll+val\|K3\|VB\|e0.002` | pass | 49.000 | a4d0b81e0568 |
| `D1\|H-R-0\|rigid\|T\|roll-op\|K1\|V0\|e0` | pass | 54.203 | 532c14c9b00f |
| `D1\|H-R-0\|rigid\|T\|roll-op\|K1\|V0\|e0.002` | pass | 54.528 | c6d0f1eab61e |
| `D1\|H-R-0\|rigid\|T\|roll-op\|K1\|VB\|e0` | pass | 53.661 | 52f16113ad62 |
| `D1\|H-R-0\|rigid\|T\|roll-op\|K1\|VB\|e0.002` | pass | 53.665 | ab9f16d04216 |
| `D1\|H-R-0\|rigid\|T\|roll-op\|K3\|V0\|e0` | pass | 52.006 | 8878611ff810 |
| `D1\|H-R-0\|rigid\|T\|roll-op\|K3\|V0\|e0.002` | pass | 53.484 | 2bc8bf3e6fd3 |
| `D1\|H-R-0\|rigid\|T\|roll-op\|K3\|VB\|e0` | pass | 52.943 | baa4cc92ac60 |
| `D1\|H-R-0\|rigid\|T\|roll-op\|K3\|VB\|e0.002` | pass | 53.401 | ce82ee09346a |
| `D1\|H-R-0\|rigid\|T\|roll-val\|K1\|V0\|e0` | pass | 53.014 | 88d3dc091454 |
| `D1\|H-R-0\|rigid\|T\|roll-val\|K1\|V0\|e0.002` | pass | 52.870 | e7aaeabd67c3 |
| `D1\|H-R-0\|rigid\|T\|roll-val\|K1\|VB\|e0` | pass | 50.814 | 79094041724e |
| `D1\|H-R-0\|rigid\|T\|roll-val\|K1\|VB\|e0.002` | pass | 51.224 | 553a60f98ffd |
| `D1\|H-R-0\|rigid\|T\|roll-val\|K3\|V0\|e0` | pass | 47.218 | 755325d7db60 |
| `D1\|H-R-0\|rigid\|T\|roll-val\|K3\|V0\|e0.002` | pass | 46.452 | d73481e0cce3 |
| `D1\|H-R-0\|rigid\|T\|roll-val\|K3\|VB\|e0` | pass | 46.496 | bd2430047454 |
| `D1\|H-R-0\|rigid\|T\|roll-val\|K3\|VB\|e0.002` | pass | 46.155 | a17f24e4a758 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K1\|V0\|e0` | pass | 28.444 | d4d2d9556f5c |
| `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K1\|V0\|e0.002` | pass | 29.505 | e10eb5e47f6c |
| `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K1\|VB\|e0` | pass | 28.459 | 349f0aea3e16 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K1\|VB\|e0.002` | pass | 27.878 | 20c1137ac869 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K3\|V0\|e0` | pass | 27.993 | 04f10312dc82 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K3\|V0\|e0.002` | pass | 27.691 | 64a12032e730 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K3\|VB\|e0` | pass | 27.425 | 2764288ae859 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K3\|VB\|e0.002` | pass | 27.212 | 4c8b3b12614e |
| `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K1\|V0\|e0` | pass | 34.541 | 2cae9fc275a6 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K1\|V0\|e0.002` | pass | 34.476 | 3e9bb7be2104 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K1\|VB\|e0` | pass | 38.414 | 7a312b42bc3a |
| `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K1\|VB\|e0.002` | pass | 38.365 | 3c951f160f3c |
| `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K3\|V0\|e0` | pass | 32.610 | 7075c89d7628 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K3\|V0\|e0.002` | pass | 32.750 | 1af4a16c2796 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K3\|VB\|e0` | pass | 35.108 | 72d944deabe7 |
| `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K3\|VB\|e0.002` | pass | 34.529 | 587e3d422a0f |
| `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K1\|V0\|e0` | pass | 26.124 | a572b832df74 |
| `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K1\|V0\|e0.002` | pass | 26.297 | 1928ffc386c8 |
| `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K1\|VB\|e0` | pass | 26.115 | 38643d1b90cd |
| `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K1\|VB\|e0.002` | pass | 26.040 | a0904d30941f |
| `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K3\|V0\|e0` | pass | 23.596 | 2f061eb4e99f |
| `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K3\|V0\|e0.002` | pass | 24.683 | 96d5a6251b6d |
| `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K3\|VB\|e0` | pass | 23.474 | 6169b459e6eb |
| `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K3\|VB\|e0.002` | pass | 22.728 | 1976b3758beb |
| `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K1\|V0\|e0` | pass | 31.871 | a42be8c348d9 |
| `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K1\|V0\|e0.002` | pass | 31.808 | 4410a5b0ef53 |
| `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K1\|VB\|e0` | pass | 36.279 | 5edfe03986a8 |
| `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K1\|VB\|e0.002` | pass | 36.067 | 5bc5b5e0e93a |
| `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K3\|V0\|e0` | pass | 28.151 | 9d4bc3c469b2 |
| `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K3\|V0\|e0.002` | pass | 29.072 | 2f3d96c761a1 |
| `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K3\|VB\|e0` | pass | 32.569 | 4284780cce82 |
| `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K3\|VB\|e0.002` | pass | 32.632 | d4c66e0ef821 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K1\|V0\|e0` | pass | 19.849 | a6fcf2e488c4 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K1\|V0\|e0.002` | pass | 20.842 | 1af1159f4055 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K1\|VB\|e0` | pass | 20.324 | e67d4b1c6dde |
| `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K1\|VB\|e0.002` | pass | 20.658 | 816dc54d4007 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K3\|V0\|e0` | pass | 17.704 | 60cabcc4c22f |
| `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K3\|V0\|e0.002` | pass | 16.771 | fafe31e33d8b |
| `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K3\|VB\|e0` | pass | 15.800 | e760b0dce96f |
| `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K3\|VB\|e0.002` | pass | 16.720 | e5f158746366 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K1\|V0\|e0` | pass | 25.728 | e5da182dacb5 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K1\|V0\|e0.002` | pass | 26.427 | 22537eb9e754 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K1\|VB\|e0` | pass | 30.918 | f8c0a4eb6a59 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K1\|VB\|e0.002` | pass | 30.486 | a42fe189a52e |
| `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K3\|V0\|e0` | pass | 22.227 | 5f9bb0546435 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K3\|V0\|e0.002` | pass | 22.666 | d3b9e45cd423 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K3\|VB\|e0` | pass | 25.042 | dc4e7b8e46e9 |
| `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K3\|VB\|e0.002` | pass | 26.302 | 86f7c2afa64a |
| `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K1\|V0\|e0` | pass | 24.330 | b89189eca3e0 |
| `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K1\|V0\|e0.002` | pass | 24.486 | 204b9ec7da7e |
| `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K1\|VB\|e0` | pass | 23.985 | bec8064cb97a |
| `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K1\|VB\|e0.002` | pass | 24.229 | 68d2c7cad29a |
| `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K3\|V0\|e0` | pass | 23.412 | 1b08b8e0bf2c |
| `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K3\|V0\|e0.002` | pass | 23.166 | f63d2b06c8b0 |
| `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K3\|VB\|e0` | pass | 22.640 | 4204e6a2f1bf |
| `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K3\|VB\|e0.002` | pass | 22.976 | 459f78ebf863 |
| `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K1\|V0\|e0` | pass | 17.850 | 8e53e1a8e8bb |
| `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K1\|V0\|e0.002` | pass | 18.259 | 7d073a5598a2 |
| `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K1\|VB\|e0` | pass | 16.899 | 9878562ef42e |
| `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K1\|VB\|e0.002` | pass | 17.594 | e0f10b25ceee |
| `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K3\|V0\|e0` | pass | 15.896 | d0728aa62a52 |
| `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K3\|V0\|e0.002` | pass | 15.740 | 2ed2f41ec6bc |
| `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K3\|VB\|e0` | pass | 15.053 | e205a524c001 |
| `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K3\|VB\|e0.002` | pass | 14.325 | db230947cc25 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K1\|V0\|e0` | pass | 45.941 | c7d7c074a8c2 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K1\|V0\|e0.002` | pass | 45.933 | b9b065c10fcc |
| `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K1\|VB\|e0` | pass | 45.025 | d9dd7c797739 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K1\|VB\|e0.002` | pass | 45.033 | 81d1ade6987a |
| `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K3\|V0\|e0` | pass | 45.939 | b8118afc448a |
| `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K3\|V0\|e0.002` | pass | 45.932 | f4d361341147 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K3\|VB\|e0` | pass | 45.031 | cc8d3dd66dc0 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K3\|VB\|e0.002` | pass | 45.028 | f2848ecc0932 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K1\|V0\|e0` | pass | 45.996 | 072234079816 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K1\|V0\|e0.002` | pass | 45.999 | 2c99c7ecec11 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K1\|VB\|e0` | pass | 45.079 | 873834eb05cf |
| `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K1\|VB\|e0.002` | pass | 45.081 | c3ef3ae2656e |
| `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K3\|V0\|e0` | pass | 46.000 | 2328cffa0903 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K3\|V0\|e0.002` | pass | 46.000 | c4949074d37a |
| `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K3\|VB\|e0` | pass | 45.082 | 8addf43497c2 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K3\|VB\|e0.002` | pass | 45.090 | ed8c55159842 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K1\|V0\|e0` | pass | 46.076 | ff91cc1c43f1 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K1\|V0\|e0.002` | pass | 46.074 | 71520280410c |
| `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K1\|VB\|e0` | pass | 45.157 | f9ee7a9dd64a |
| `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K1\|VB\|e0.002` | pass | 45.154 | 6ee416c3b15d |
| `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K3\|V0\|e0` | pass | 46.075 | 5e25dfa5b61c |
| `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K3\|V0\|e0.002` | pass | 46.075 | 6a89f52bc5d2 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K3\|VB\|e0` | pass | 45.161 | 109f5578a634 |
| `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K3\|VB\|e0.002` | pass | 45.160 | a12ae4955fae |
| `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K1\|V0\|e0` | pass | 45.904 | 56f9be6d9c47 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K1\|V0\|e0.002` | pass | 45.897 | ede6341a27dc |
| `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K1\|VB\|e0` | pass | 44.778 | 1ac083e50c8f |
| `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K1\|VB\|e0.002` | pass | 44.775 | cb852e704aab |
| `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K3\|V0\|e0` | pass | 45.901 | 57f80642d1a6 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K3\|V0\|e0.002` | pass | 45.898 | 1f7753316705 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K3\|VB\|e0` | pass | 44.775 | 68a14b2b0dd7 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K3\|VB\|e0.002` | pass | 44.773 | d4825b1754f6 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K1\|V0\|e0` | pass | 45.959 | cf70a110ccbf |
| `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K1\|V0\|e0.002` | pass | 45.953 | 7f86416c6c03 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K1\|VB\|e0` | pass | 44.823 | d721b88f3bdd |
| `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K1\|VB\|e0.002` | pass | 44.827 | 4645184b875a |
| `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K3\|V0\|e0` | pass | 45.956 | 8917ce2fd0c9 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K3\|V0\|e0.002` | pass | 45.957 | adb4f5955f51 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K3\|VB\|e0` | pass | 44.829 | a0acfaee784d |
| `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K3\|VB\|e0.002` | pass | 44.828 | 13dba830a93d |
| `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K1\|V0\|e0` | pass | 46.043 | 7e5405f3a003 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K1\|V0\|e0.002` | pass | 46.046 | b6613e9638e4 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K1\|VB\|e0` | pass | 44.902 | d86a6f5ca71d |
| `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K1\|VB\|e0.002` | pass | 44.898 | d7b76acc55ff |
| `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K3\|V0\|e0` | pass | 46.044 | b689238fc9c6 |
| `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K3\|V0\|e0.002` | pass | 46.043 | a2ddcb84f49c |
| `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K3\|VB\|e0` | pass | 44.904 | 64c527af15ee |
| `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K3\|VB\|e0.002` | pass | 44.904 | 1c20226394ae |
| `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K1\|V0\|e0` | pass | 45.495 | 8d21f8ed1127 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K1\|V0\|e0.002` | pass | 45.910 | e1c5cd6942f3 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K1\|VB\|e0` | pass | 44.647 | 468ccc8c6855 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K1\|VB\|e0.002` | pass | 44.648 | 13abfab8adeb |
| `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K3\|V0\|e0` | pass | 44.715 | 397bcb99eeaf |
| `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K3\|V0\|e0.002` | pass | 44.831 | 597aee69477f |
| `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K3\|VB\|e0` | pass | 44.654 | b6420c7a1e70 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K3\|VB\|e0.002` | pass | 43.701 | 49e7f3a8bec3 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K1\|V0\|e0` | pass | 45.989 | 9cfd55090bd9 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K1\|V0\|e0.002` | pass | 45.980 | 6e337848ba8c |
| `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K1\|VB\|e0` | pass | 44.694 | 8a69ae726def |
| `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K1\|VB\|e0.002` | pass | 44.698 | a79d46a88860 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K3\|V0\|e0` | pass | 45.982 | 121f7bcf9f97 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K3\|V0\|e0.002` | pass | 45.985 | e91ffa77eb96 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K3\|VB\|e0` | pass | 44.700 | 0ecf853c3d92 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K3\|VB\|e0.002` | pass | 44.695 | db797088ee29 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K1\|V0\|e0` | pass | 46.090 | f141f38604b8 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K1\|V0\|e0.002` | pass | 46.084 | ad9554e57976 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K1\|VB\|e0` | pass | 44.763 | 33785bd1301d |
| `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K1\|VB\|e0.002` | pass | 44.766 | 3a4488a2ba85 |
| `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K3\|V0\|e0` | pass | 45.060 | 390984a35c3c |
| `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K3\|V0\|e0.002` | pass | 44.395 | 0987d8865e4f |
| `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K3\|VB\|e0` | pass | 44.564 | b79d3601146f |
| `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K3\|VB\|e0.002` | pass | 43.339 | 4d9f0e0bf393 |
