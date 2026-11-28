# v5 논문 A형(경사계) 재실행 묶음 규칙 — 초안 (control-expert, 2026-11-22 작성, 봉인 전, 수정 11 2026-11-28)

- 상태: **초안**이다. 판정 문서가 아니다. 봉인 순서는 다음과 같다.
  1. (끝남) stats 검토 1~3(`v5paper_imua_stats/stats_review_draft1_20261122.md`, `stats_review_rev2_rev26_20261122.md`, `stats_review_rev3_20261122.md`)
  2. (끝남) 수정 4~10(`v5paper_imua_rules_draft.md` 수정 10, 커밋 `c77b1dcf`)
  3. 수정 11(이 판). 원판 파일 `v5paper_imua_rules_draft.md`는 고치지 않았고 이 파일이 수정 11의 전문이다.
  4. stats 검토 4: 8절 확인 필요 Q-S1. E-1·E-2 기대 건수, `u3_neff.py`, 4.2.1 E-2 계산 정의
  5. 봉인 전 채울 칸(10절)
  6. 봉인: `v5paper_imua_rules.md`와 `.sha256`. 함께 고정할 파일은 10절에 적었다.
  7. verif-protocol-auditor `[시점] 실행 전`
- **요청 밖 추가(수정 11)**: 아래 다섯 가지는 요청받지 않았지만 작성자가 더했다. 각 항목의 채택 여부는 8절에서 묻는다.
  1. J-2c(3.4절): TA의 Chrono C-5 판정 도구가 436.8 모드에서 같은 결과를 내는지 보는 관문
  2. H-12(T4h 재생 기록)를 A형 묶음에서 해당 없음으로 처리(2.2절)
  3. C-5 경로 2 CD-7 처리(436.8 결정 107 (2))를 A형에 그대로 적용한다는 것을 결과 전에 고정(4.1절)
  4. E-2 계산 정의 두 곳 수정(4.2.1절 (iv)의 판독 수, 기록 끝에 걸치는 창)
  5. A형 판정 실행본 절(3.5절, 빈칸 포함)
- 수정 이력
  - 수정 1: Q-J1, E-8 삭제, Q-U6 코드 확인, U-6 건수
  - 수정 2: stats 검토 1, 사용자 결정 1~5, Q-U6 (가), H-4 행 수, A형 기대 태그, 상태 순서
  - 수정 3: stats 검토 2(B-3 재표집 단위, R-6, R-7, R-10, R-11, R-12), 4.4 관문 ID
  - 수정 4: stats 검토 3(S-3 유효 표본 수 실측, S-5 포괄률, S-6 g8 가중 공개, S-7 E-1 재표집 문장 정정, S-8 음성 대조)
  - 수정 5: verif rev26 봉인 전 감사 B-1(사용자 결정 (가)). A형 판정 도구 커밋 TA를 T26과 분리, P-4 고침, J-2 추가, A형 판정의 RD-1 4·5 대체 조건(3.1절)
  - 수정 6: verif rev26 재감사 A-1(J-2가 돌 수 있게 436.8 모드 허용 인자, J-2 비교 제외 열거, TA 커밋당 1회), R-d(J-2 출력은 rev26 낱말 아님)
  - 수정 7: verif rev26 재재감사 A-2(J-2 실행본 = T26 5단계 실행본 + 변경, 경로 2 실행본 관문, ta_identity.json 고정)
  - 수정 8: verif rev26 네 번째 재감사 W-i(TA worktree 깨끗함 기록), W-k(`--allowed-src-changes`를 두 경로 도구 모두에)
  - 수정 9: verif rev26 다섯 번째 재감사 B-5(사용자 결정 (가): T26 경로 2 `--data-root`와 경로 1 실행본 입력 인자를 TA·J-2·A형 판정에 그대로 쓴다, TA가 더하는 입력 읽기도 같은 기준, J-2 제외 1a), 기록 3(경로 2 `--allowed-src-changes`는 받기만 함)
  - 수정 10: verif rev26 여섯 번째 재감사 W-n(J-2 제외 1a 삭제: `c2_py_sha256`은 저장 입력 메타), rev26 부록 r5(B-6)
  - **수정 11**: python 구현 보고 `imu_attitude_only/imua_seal_prep/impl_resume_20261128.md` 6절의 확인 필요 1~5·7·8, 준비 보고 `imua_seal_prep/report.md` 3.2절의 G-a~G-f, 사용자 결정 11-26·11-28을 반영했다. 바뀐 곳은 다음과 같다.
    - 1.1절 `imu_sensor` 블록 비교, 1.2절 IND 경사계 입력
    - 2.1절 출력 이름 표, 2.2절 기록 위치·키
    - 3절 상태 갱신, 3.1절 TA 정의와 허용 집합(G-b 포함), 3.2절 J-2 기준을 T26′ 2회차로 바꿈
    - 3.3절 TA 작성 명세(경로별), 3.4절 J-2c, 3.5절 A형 판정 실행본
    - 4.1절 묶음 범위·CD-7, 4.2.1절 E-2 계산 정의
    - 6·8·10절 갱신
- 사용자 결정
  - 2026-11-22
    - A형을 유지한다(v5 논문 본문은 A형 결과로 쓴다).
    - 판정 문턱은 436.8 봉인값 그대로 쓴다.
    - 시간 항목과 READY 유지 미달은 A형 한계로 보고한다.
    - 축소안: 하네스 D-1·U-3·U-6, Chrono 3단계(C-5)
    - IND·IND_LAS도 같은 경사계로 돌린다.
  - 2026-11-26(decision_log 837행)
    - 기준 제어기는 v5 제어기다(`final_C4G2_LAS_K1`, VB `final_C4G2_P3_LAS_K1`, 판 8과 무관).
    - 이득은 `v5_A`다.
    - C-5 T4/T5 재생기 A형 보완(P-8, 무대체 재생 동일성 관문)을 한다.
    - 기준 커밋은 v5-imua로 유지한다. 판 5 코드 파일은 허용 집합에 넣고 비트 동일 근거를 붙인다.
    - rev26 T26과 A형 구현은 판 8과 병행한다. 본 실행은 따로 승인받는다.
  - 2026-11-28(decision_log 836행)
    - v5는 현 v5 제어기 + A형으로 닫는다.
    - 436.8은 현행 IMU 짝 비교 자료로만 쓴다. 한계 절에 "사전 등록 판정 불가, rev26 사후 재판정 종합 미달(참고)"을 적는다.
    - 합격 주장은 A형 봉인 결과로만 한다.
- 덧붙임 대상: 여기 적지 않은 정의·문턱·두 경로 절차는 아래 문서의 판 그대로다.
  - 436.8 규칙 원판·개정판(`v5_resume_4368_rules.md` … `rev25.md`, `rev26.md`)과 rev26 정오 1~3(`v5_resume_4368_rules_rev26_erratum{1,2,3}.md`), 각 `.sha256`
  - 436.8 판정서 두 개(`v5_resume_4368_judgement.md`: Chrono, R3f `8a0c843`; `v5_resume_4368_harness_judgement.md`: 하네스, 13절 rev26 덧붙임 포함)
  - 등급 대조 표 `judge_932f1fb/_fixed/grade/r4_grade_compare_table.md`
- 규약
  - 10 Hz($T_s$ = 0.1 s), 출력 지연 d = 1
  - C2는 음되먹임이다(다리 행정 속도 명령 [m/s], + = 신장).
  - 힘은 실린더 순 힘 [N]이다. $F_{min}$ = 9,414.589 N.
  - 각도 [°], 각주파수 [rad/s]

### 기호

| 기호 | 뜻 |
|---|---|
| M4 | `932f1fb1724f074e4ee93a9c02193c7c840d13c4`(436.8 R4 하네스 판정 기준) |
| T26′ | `74c27846cbfab498bd59340d1eaec344f1596b0b`(rev26 정오 3, 5단계 2회차 도구 커밋, 바탕 M4, 브랜치 `rev26-t26b`) |
| R2 | `b9f5707d7f3f7a26230b25f4edbc1fec587ca612`(436.8 실행 커밋) |
| R3f | `8a0c8432d23c9db0916bf6f9cb9139466bd32551`(436.8 Chrono 판정 도구 커밋) |
| H_I | v5-imua 브랜치에서 A형 실행 코드(P-1·P-2·P-5·P-6·P-7 실행 쪽·P-8·C-1)가 모두 들어간 커밋. 지금 후보는 `b04167248a49cfc4435a3b80e6baedef0713771e`이다. C-1과 P-7 나머지가 남아 있어 아직 확정되지 않았다 |
| RA | A형 실행 커밋. RA = H_I |
| TA0 | T26′과 H_I의 병합 커밋(3.1절) |
| P1A / P2A | TA0 위의 경로 1 / 경로 2 A형 판정 모드 커밋(3.3절) |
| TA | A형 판정 도구 커밋 = TA0 + (P1A ∪ P2A)(3.1절) |

## 1. A형 설정과 이득 선택 (결과를 본 뒤의 선택, 공개)

| 항목 | 값 |
|---|---|
| 센서 | 경사계: 내부 2차 Bessel 1 Hz, 출력 지연 20 ms, 분해능 0.01°, 100 Hz 출력, 각속도·$f_z$ 없음(지연·분해능은 가정). 하네스는 오차 없는 원시 IMU를 거친다. Chrono도 경사계는 이상 등급(필터·지연·분해능만, G-e, 가정)이다 |
| C2·ABL 제어기 | 436.8과 같은 제어기에 `C2Config.with_imu_outputs("attitude", probe_cue="off", …)`를 더한다. D1′ `explained`, B1′ 없음, GE1′ 자세 차분 |
| C2 이득 | **`v5_A` = Kp 0.10 s⁻¹, Ki 0.004 s⁻², K_g 0.08 s⁻¹**(사용자 결정 2026-11-26) |
| IND·IND_LAS | `c8` 기준선 제어 상수는 그대로 둔다. 센서 입력만 경사계로 바꾼다(1.2절, P-6) |

**A형 기대 태그**(`controller_tag`, Chrono `--expect-controller`). 436.8 원판 4.1 표의 태그에 `_IMUA`를 붙인 것이다.

| 행 종류 | 기대 태그 | `imu_sensor` 기대 블록(1.1절) |
|---|---|---|
| V0·V0v(하네스) | `final_C4G2_LAS_K1_IMUA` | `harness_c2` |
| VB(하네스) | `final_C4G2_P3_LAS_K1_IMUA` | `harness_c2` |
| ABL(U-6) | `ABL_LAS_K1_IMUA` | `harness_c2` |
| IND(U-6) | `IND_IMUA` | `harness_ind` |
| IND_LAS(U-6 기록) | `IND_LAS_IMUA` | `harness_ind` |
| C-5 V0·VB(Chrono) | 위 V0·VB 문자열 | `chrono_c2` |

- 태그는 위 문자열과 **그대로 같은지**로 비교한다.
  - `v5_options`의 접미사 떼는 술어는 ③ 판별에만 쓴다.
  - 다르면 S-2다(원판 80·281행).
  - `controller` 필드만 다르면 281행 둘째 구("한 묶음 안에 두 판이 섞였다")로 읽어 S-2다.
- 정체성 표본(3절)은 접미사 없는 436.8 태그(원판 4.1 표)를 쓴다. 그 줄·행에는 `imu_sensor`와 `imua_*` 키가 없어야 한다. 있으면 S-2다.

### 1.1 `imu_sensor` 블록 비교 범위 (수정 11, 확인 필요 5)

- **블록 전체를 비교한다**(키 집합과 값 모두). 기대값은 봉인 때 고정하는 `v5paper_imua/imua_expected_imu_sensor.json`이다. 칸은 셋이다.
  - `harness_c2` = RA의 `imu_a_harness.ImuSetting("inclinometer", "v5_A").to_meta()`
  - `harness_ind` = 같은 설정의 `industry_meta()`
  - `chrono_c2` = C-1 구현이 `controller_meta.imu_sensor`에 쓰는 블록
- `chrono_c2`가 `harness_c2`와 다를 수 있는 키는 `raw_imu`(원시 IMU 설명 문자열) 하나뿐이다. 다른 키가 다르면 봉인하지 않는다.
- 이 파일은 봉인 전에 RA checkout에서 생성 스크립트(P-7, 10절)로 만든다. 사람이 손으로 쓰지 않는다.
- 비교 방법
  - JSON을 읽은 값끼리 같은지 본다(키 순서 무관, 수는 JSON 수 그대로).
  - 블록이 없거나 다르면 S-2다. 4368 모드에서는 이 블록을 읽지 않는다.
- 이 실행은 GE1′ 잡음 0으로 돈다. 그러므로 블록에 `rate_noise_std` 키가 있으면 다름이다.
- 근거: 실제 블록(구현 `imu_a_harness.py` 122~149행 @`b0416724`)은 수정 10 표의 `{"model", "gains_preset"}`보다 큰 상위집합이다. 게인 수치, `sensor`(필터·지연·분해능), `raw_imu`, `controller`가 더 들어 있다. 키 일부만 보면 "프리셋 이름은 같고 게인·센서 파라미터는 다른" 줄을 놓친다.

### 1.2 IND·IND_LAS의 경사계 입력 (수정 11, 확인 필요 4: 제어 쪽 판단)

- **해석**: `AttitudeEstimator`는 "비력 → 기울기" 단계와 그 뒤의 자세 저역통과(τ 0.8 s × 2, 10 ms 표본)로 되어 있다(`03_src/outrigger_sim/sensors/attitude.py` 107~138행).
  - A형은 앞의 "비력 → 기울기" 단계만 경사계 각도로 바꾼다.
  - 저역통과, C8 완료 필터, C8 상수는 그대로 둔다(`b5_baseline_compare.py` 404~425행 @`b0416724`, `IND_ATTITUDE_TIME_CONSTANT_S` 0.8, `IND_ATTITUDE_STAGES` 2).
  - C2 A형도 같다. 경사계 표본이 `update_angles`로 같은 저역통과에 들어간다(`c2.py` 5547~5565행 @`b0416724`).
- **이 해석이 맞다**(control-expert 판단). 이유는 세 가지다.
  1. 저역통과는 센서가 아니라 C8 루프 설계의 일부다. 그 시정수는 Q-U6 (가)의 "C8 상수"에 들어간다.
  2. 저역통과를 건너뛰면 IND의 제어 법칙이 바뀐다. 아래 표처럼 위상 여유가 크게 오르므로, 센서 효과가 아니라 더 빠르고 강건한 다른 비교 제어기가 된다.
  3. C2 A형과 처리가 같아야 U-6에서 C2와 IND를 비교할 수 있다.
- **소신호 여유**(가정 모델, 판정 아님)
  - 모델: 연속 근사, 음되먹임, $L(s) = K\,F(s)\,e^{-sT}/s$
  - $K$ = C8 `fine_gain_1_s` 0.5 s⁻¹(다리 기하가 상쇄된다고 가정)
  - $T$ = 출력 지연 0.1 s + ZOH 0.05 s(+ 경사계 0.02 s)
  - $F$ = 저역통과 $1/(0.8s+1)^2$ × (경사계) 2차 Bessel 1 Hz(직류 군지연 0.217 s)

| 경우 | ω_gc [rad/s] (Hz) | PM [°] | ω_pc [rad/s] | GM [절대 / dB] | $M_s$ | 지연 여유 [s] |
|---|---|---|---|---|---|---|
| 현행 IMU(기울기 → 저역통과) | 0.444 (0.0707) | 47.1 | 1.065 | 3.67 / 11.3 | 1.79 | 1.85 |
| **A형, 저역통과 유지(채택)** | 0.443 (0.0706) | 41.1 | 0.883 | 2.66 / 8.5 | 2.07 | 1.62 |
| A형, 저역통과 건너뜀(채택 안 함) | 0.499 (0.0794) | 78.9 | 4.088 | 9.43 / 19.5 | 1.18 | 2.76 |

- 계산: 두 방법으로 했다. 정확한 지연을 넣은 조밀 주파수 스윕(4×10⁵점)과 6차 Padé 근사에 `ct.margin`을 쓴 것이다. 두 값의 상대차는 ≤ 2×10⁻⁵이다(Padé 근사 차).
  - Julia 교차 검증은 하지 않았다.
  - 명령 램프·끝 단계 논리·비선형은 모델에 없다.
- **공개(기록)**
  - C2는 A형에서 이득을 다시 골랐다(`v5_A`). IND는 C8 상수를 그대로 둔다(Q-U6 (가)).
  - 그래서 IND A형은 여유가 줄어든 채 비교된다(위 모델로 PM −6.0°, $M_s$ +0.28).
  - U-6 C2↔IND 비교를 해석할 때 이 차를 함께 적는다.

**공개**: 이득은 같은 50키 하네스 확인 실행 두 번(`v5/imua_check/` A-v5, `v5/imua_check_a2/` v5_A2) 결과를 본 뒤 골랐다.
- 두 실행 모두 결과 전에 고정한 관문에서 fail이었다(검토 `imua_check_review.md`, `imua_check_a2_review.md`).
- 이 묶음의 결과는 아직 보지 않았다.

| 기준(우선순위 순) | A-v5 | v5_A2 | 선택 |
|---|---|---|---|
| ① READY를 선언한 뒤 잃음(개정 2 G5b, VB 34줄) | 2줄(1 집락: S5 η 0.80) | 5줄(3 집락) | A-v5 |
| ② 선형 여유(전체 J, C0·C2·C4, 최악 M_s) | 1.452(여유 0.048) | 1.473(여유 0.027) | A-v5 |
| ③ U-9 표적 실패(G4·G4d) | G4 7키(S2 T4 21.5 s ×4, S5 T1 ×3), A형만의 D 행 2행 | G4 4키(S5 T4 25~30 s ×4), A형만의 D 행 2행 | 비슷함 |
| ④ 첫 READY 지연(A − R0 중앙값) | 약 +16 s | +14.6 s(A2 − A-v5 중앙값 −3.5 s) | v5_A2 |
| ⑤ 경계 경사 S7 | 행정 여유 안전 정지 | 같음 | 같음 |

- READY 유지(①)와 강건성(②)을 시간(④)보다 앞에 둔다.
  - READY를 선언한 뒤 다시 LEVEL로 가는 동작은 운용상 지연보다 나쁘다.
  - 이득을 더 올릴 여유는 M_s 기준에서 막혀 있다.
- 기준 ①의 차(사건 집락 1/13 대 3/13)는 Fisher 양측 p ≈ 0.59로, 우연과 구별되지 않는다. 같은 50키에서 골랐으므로 v5_A의 확인 실행 비율은 낮은 쪽으로 치우칠 수 있다.
- 두 확인 실행 결과는 판정에 쓰지 않는다. 4.2절 해석 보조(상한·기대 건수·양성 대조의 입력)에만 쓴다.

## 2. 실행 목록 (축소안)

| 묶음(436.8 이름) | 내용 | 줄·행 | 엔진 | 짝 |
|---|---|---|---|---|
| H-1 D-1 | D-1 하네스 전부(`d1` 키 목록 그대로) | 868(V0 434 + VB 434) | 하네스 run_v5 | 436.8 H-1 |
| H-2 D-1 선별 | H-1 결과로 선별 규칙만 계산한다(기록). 선별된 Chrono 행(436.8 C-1~C-3·PS-c)은 이 축소안에서 돌리지 않는다 | 계산 | — | 436.8 H-2 |
| H-3 U-3 | v4 묶음 재실행 전부. slope V0의 D-1 재사용 12줄은 436.8처럼 H-1 출력에서 가져온다(원판 115행) | 2,228(1,114키 × V0·VB) | 하네스 | 436.8 H-3(rev26 재판정 뒤 등급) |
| H-4 U-6 | VB: C2·ABL·IND 각 242 = **판정 726**, IND_LAS **기록 242** | 968 | 하네스 | 436.8 H-4(rev26 재판정 뒤 등급) |
| C-5 3단계 Chrono | 436.8 C-5 35행(L2b 24 + SCM 11) 그대로 | 35 | Chrono L2b·SCM. `--threads`·`OMP_WAIT_POLICY=PASSIVE`·P/E 풀을 기록하고, 436.8 행과 같은 스레드 수를 쓴다 | 436.8 C-5 |
| I-H 정체성 표본(하네스) | 현행 IMU·436.8 태그로 같은 커밋에서 다시 돌린다(3절 선정 규칙) | 50 | 하네스 | 436.8 같은 키 줄 |
| I-C 정체성 표본(Chrono) | 현행 IMU로 C-5 L2b 가장 짧은 1행 + SCM 가장 짧은 1행 | 2 | Chrono | 436.8 같은 행 |

- 돌리지 않는 묶음(R-13 주장 목록에 공개)
  - U-9(H-5), dg3, 잡음(r79 3,006 + 100), main·격자(1,676)
  - D-1 Chrono(C-1~C-3), LAS Chrono(C-4), J_P(12행), 열린 루프(C-6·C-7, 제어기 없음)
  - **H-6~H-12 하네스 기록·판정 묶음 전부**(축소안 밖, 2.2절 H-12 참조)
- U-9는 `imua_check` A-v5 42 job을 인용한다. **A형 근거 낱말은 fail(G1·G4·G5b)이다**(기록, 판정 아님).
- 비용(추정, compute-scheduler가 436.8 저장 `wall_s`로 다시 잡는다)
  - 하네스: (868 + 2,228 + 968 + 50) × 약 58 s × A형 연장 1.25 ≈ **83 코어·h**(±10 %). 근거 등급은 plan이다. 구현 스모크 시간은 근거로 쓰지 않는다.
  - Chrono: L2b 25행 × 4~15분 + SCM 12행 × 1~3 h × 4 스레드 ≈ **55~150 스레드·h**
  - 러너는 `~/.claude/runners/outrigger_control-v5paper-imua/`에 두고 예약·감시한다(전역 §3·§4).

### 2.1 출력 이름 표 (수정 11, 확인 필요 8, G-c)

`<RA7>`·`<TA7>`은 RA·TA 전체 해시의 앞 7자다. 같은 RA·TA로 두 번 돌리는 일은 없다(6절).

| 묶음 | 결과 파일 | A형 기록 폴더 | 명령 꼴 |
|---|---|---|---|
| H-1 | `06_analysis/02_control/verif_matrix/v5paper_imua/run_<RA7>/h1_d1.jsonl` | `…/run_<RA7>/h1_d1_imua/` | 436.8 `resume_k1_steps.run_v5_step`과 같고 끝에 `--imu-model inclinometer --imu-gains v5_A`를 붙인다. `--out`은 필수다 |
| H-3 U-3 | `06_analysis/02_control/v5_rerun/imua_<RA7>/<436.8 u3_steps 출력 파일 이름>`(18개) | `<그 파일 stem>_imua/` | 436.8 `u3_steps` + 같은 두 인자. slope·h9의 `--reuse-d1`은 위 H-1 결과 파일을 가리킨다 |
| H-4 U-6 | `06_analysis/02_control/v5_rerun/imua_<RA7>/<436.8 u6_steps 출력 파일 이름>`(4개) | `<그 파일 stem>_imua/` | 436.8 `u6_steps` + 같은 두 인자 |
| I-H | `06_analysis/02_control/verif_matrix/v5paper_imua/run_<RA7>/ih/ih_d1.jsonl`, `…/ih/<436.8 U-3·U-6 출력 이름>` | 없음(현행 IMU에서는 `_imua` 폴더가 생기지 않는다) | 현행 IMU(두 인자 없음), 3절 선정 목록 |
| C-5 | `07_results/S9/batch_V5-IMUA-C5_<stamp>/`(SCM). L2b 사례 폴더는 C-1 구현이 정하는 꼴이고, 배치 ID 토큰은 `V5-IMUA-C5`다 | 사례 폴더 안 `imua_attitude.npz` | C-1 명세 |
| I-C | 배치 ID 토큰 `V5-IMUA-IC` | 없음 | 현행 IMU |
| G-d(선택, 8절 Q-U1) | 배치 ID 토큰 `V5-IMUA-GD` | 있음 | 판정·예측에 쓰지 않는다 |
| A형 판정 | `06_analysis/02_control/verif_matrix/v5paper_imua/judge_<TA7>/{harness_path1,harness_path2,chrono_path1,chrono_path2}/` | — | 3.5절 |
| J-2 | `06_analysis/02_control/verif_matrix/v5_resume_4368/judge_j2_<TA7>/{harness_path1,harness_path2}/` | — | 3.2절 |
| J-2c | `06_analysis/02_control/verif_matrix/v5_resume_4368/judge_j2c_<TA7>/{chrono_path1,chrono_path2}/` | — | 3.4절 |
| 4.2 분류 | `06_analysis/02_control/verif_matrix/v5paper_imua/classify_<TA7>/` | — | P-7 분류 스크립트 |
| 정체성·허용 목록 | `06_analysis/02_control/verif_matrix/v5paper_imua/`의 `ta_identity.json`, `ta_allowed_changes.tsv`, `allowed_src_changes.txt`, `ta_closure.json`, `imua_expected_imu_sensor.json` | — | 3.1절, 1.1절 |

- **스캔 범위**: A형 판정·분류·짝 기록은 이 표의 현재 `<RA7>`·`<TA7>` 폴더만 읽는다. 다음은 스캔 범위 밖이다.
  - `imua_check*`
  - `judge_j2_*`·`judge_j2c_*`
  - 다른 `<RA7>`의 `run_*`·`imua_*`
  - `V5-IMUA-GD` 배치
  - `v5_rerun/` 바로 아래의 436.8 출력
- 이 출력들은 git 밖이다(`07_results`, `v5_rerun` 결과). 메인 checkout에서 읽는다(rev26 2절 '입력 기준').

### 2.2 A형 기록의 위치와 키 (수정 11, 확인 필요 2)

- T4h 폴더(`<stem>_t4h/`)와 기존 T4h 파일은 바꾸지 않는다. A형 자세 기록은 **형제 폴더 `<결과 파일 stem>_imua/`**에 따로 둔다. 436.8 판정 도구가 `<stem>_t4h/`를 훑기 때문이다(`imua_records.py` 28~31행 @`b0416724`).
- 기록 파일
  - 꼴은 `imua_attitude/1`(npz)이다.
  - 이름은 `<줄 표지>_<줄 정체성 SHA-256 앞 12자>.npz`다.
  - 배타적으로 쓴다. 비어 있지 않은 기록 폴더는 거부하고(run_v5 resume만 예외), 기존 파일은 덮지 않는다.
- 배열
  - `t_s`, `phase`, `command_m_s`
  - `attitude_filtered_deg`, `attitude_true_rad`
  - `inclinometer_t_s`, `inclinometer_rad`, `attitude_true_at_inclinometer_rad`
  - `true_force_N`, `true_force_min_N`
  - `meta_json`: `form`, `identity`, `controller_tag`, `imu_sensor`, `F_min_N`, `events`
  - 정의는 `imua_records.py` 12~26행 @`b0416724` 표 그대로다.

| 묶음 | 줄 위치 | 태그 | `imu_sensor` | G5 입력 | 기록 파일 이름 | 기록 폴더 |
|---|---|---|---|---|---|---|
| H-1 D-1(`run_v5`, jsonl 한 줄) | 줄 최상위 | `controller_tag` | `imu_sensor` | `imua_check_g5` | `imua_record_file` | 결과 파일과 같은 폴더의 `<stem>_imua/` |
| H-3 U-3·H-4 U-6(`v5_rerun` 화면) | 각 레코드의 `v5` 블록 | `v5.controller_tag` | `v5.imu_sensor` | `v5.imua_check_g5` | `v5.imua_record_file` | 그 화면 결과 파일의 `<stem>_imua/` |
| H-3 slope의 D-1 재사용 12줄(`reuse` = `"d1"`) | `v5` 블록(D-1 줄에서 옮김) | 같음 | D-1 줄 값 | D-1 줄 값 | D-1 줄 값 | `v5.imua_record_source` = **H-1 기록 폴더의 이름**(`h1_d1_imua`). 읽는 쪽은 `<H-1 결과 파일 폴더>/<imua_record_source>/<imua_record_file>`로 푼다. H-1 결과 파일 위치는 2.1절 표가 정한다 |
| C-5 Chrono | `result.json` | `controller_tag`(= `c2_setup.expect_controller.name`) | `controller_meta.imu_sensor` | 없음 | 사례 폴더의 `imua_attitude.npz`(이름 고정) | 사례 폴더 |

- **키 존재 규칙**: 판정 줄·행마다 이 표의 키가 모두 있어야 한다. 없으면 그 줄의 4.2 분류는 "서명 평가 불가(배열 없음)"다. 판정 낱말은 바뀌지 않는다.
  - 기록 파일이 가리키는 위치에 없거나 `meta_json.controller_tag`가 줄 태그와 다르면 **기록 불완전**이다. 이것은 기록 실패이고 판정 실패가 아니다(4.1 상태 순서 밖, 판정서에 수를 적는다).
- **H-12(T4h 재생 기록)**: A형 묶음에서는 부르지 않는다(**해당 없음(축소안 밖)**, 요청 밖 추가 2, 8절 Q-U3).
  - 하네스 T4h 재생기의 `_IMUA` 거부(구현 보고 2절 P-8 끝)는 바꾸지 않는다.
  - H-12는 436.8에서도 경로 1만의 기록이었다(등급 대조 표 115행).

## 3. 구현 전제 (**모두 충족 전에는 실행하지 않음**)

| # | 담당 | 내용 | 현재 상태(2026-11-28 확인) | 완료 확인 |
|---|---|---|---|---|
| J-1 | rev26 | rev26: H-3·H-4 두 경로 판정 도구 보완과 436.8 재판정 | **충족**. T26′ `74c27846`로 5단계 2회차(2026-11-27 00:10~00:13). 경로 1 = 1, 경로 2 = 0, 비교기 = 1. 판정 후 감사 차단 0, (a)~(h) 일치. 판정서 13절. 판정 도구 실행 횟수 2를 공개(decision_log 839~841행) | — |
| P-1 | python | 경사계 센서 모델·`with_imu_outputs`가 실행 커밋에 들어감 | H_I 후보 `b0416724`에 있다 | 실행 커밋 포함, 기본값 비트 동일(3.1절 허용 목록 근거 칸) |
| P-2 | python | 하네스 센서 갈고리 `--imu-model inclinometer --imu-gains v5_A`, 태그 `_IMUA`, U-3·U-6 러너 | `dc67af47`. 화면 4개, 거부 조합 3, A형 스모크 10런, 기본값 스모크 9런 `commands_sha256` 같음 | 건식 목록에서 1절 기대 태그와 1.1절 블록 확인. **A형 `--reuse-d1` 경로(`u3_reuse.py` 279~280행)를 건식 1회로 확인**: slope 재사용 1줄에서 `v5.imua_record_source`·파일 존재(구현 보고 3절: 검증 공백) |
| P-4 | python(경로별 새 인스턴스 2) | A형 판정 도구 커밋 TA(3.1·3.3절) | 미착수 | 3.1절 대체 조건 1~6, 판정 행 수(3.3.1 [정의 A-3]), J-2·J-2c 통과 |
| J-2 | 메인 + verif | TA의 436.8 모드 하네스 동일성(3.2절) | 없음(TA 뒤) | 비교 결과 파일, 실행 기록 |
| J-2c | 메인 + verif | TA의 436.8 모드 Chrono C-5 동일성(3.4절, 요청 밖 추가 1) | 없음(TA 뒤) | 비교 결과 파일, 실행 기록 |
| P-5 | python | 모든 A형 줄에 `imua_check_g5`(개정 2 필드)와 2.2절 자세 기록 | `dc67af47`(`imua_records.py`) | 건식 1키에서 `key_presence.py`(2.2절 키)·`--npz-dir`(배열) 확인 |
| P-6 | python | IND·IND_LAS 경사계 입력(1.2절 해석) | `dc67af47` | 인자가 없으면 IND 1키 비트 동일, 있으면 메타 `harness_ind` 블록 |
| P-7 | python(분류·선정) / stats(기대 건수 방법) | 4.2 분류 스크립트, E-1·E-2 기대 건수 스크립트, 정체성 표본 선정, `u3_neff.py` 수정(S-4), **기대 블록 생성 스크립트(1.1절)**, **`run_v5 d1` 키 부분집합 인자**(I-H D-1 줄용. 목록 파일의 job 키만 돌리고 모르는 키는 거부), 4.4 관문 ID 상수 | 일부(`b0416724`): 분류 서명·결합·대조(저장 확인 실행 기록으로 13/13 기대대로), I-H 선정(모집단 4,064줄, 후보 sha `29d451b1…`). **E-2 계산 정의 수정 2건(4.2.1절)이 아직 반영되지 않았다** | 단위 시험, 양성·음성 대조를 RA에서 다시 실행(sha 고정), 건식 |
| P-8 | python | C-5 T4/T5 재생기 A형 기록 재구성(사용자 결정 11-26) | `d5df6201`(경로 1 재생기) | 3.3.1 [정의 A-7]. 실제 A형 Chrono 행 수용 시험은 G-d 행 또는 C-5 첫 행에서 한다 |
| C-1 | cad | Chrono `run_S8C`(L2b)·`run_S9`(SCM)에 `--imu-model inclinometer --imu-gains v5_A`, `--expect-controller …_IMUA`, `SensorSuite(attitude_sensor=INCLINOMETER)`, 2.2절 자세 기록. `pychrono.sensor`는 쓰지 않는다. 명세는 구현 보고 7절 | **없음** | 인자가 없으면 짧은 강체 1행 비트 동일, 인자가 있으면 메타 `chrono_c2` 블록(1.1절) |
| G-d | 메인 | (선택, 8절 Q-U1) C-5 35행 밖 짧은 L2b 1행으로 A형 가동 확인 | 사용자 결정 전 | 값은 판정·예측에 쓰지 않고 공개 |
| G-1 | 메인 | RA를 고정한 worktree(`git worktree lock`)와 `is_clean` | v5-imua worktree는 잠기지 않음 | 러너 기록 |

- J-2 비교에서 rev26 부록 A 규범 규칙(r6) 밖으로 더 빼는 TA 정체성 필드는 아래 셋뿐이다.
  1. 모든 출력의 `v5_options` 하위 나무(TA는 T26′ 대비 `v5_options.py`를 바꿈)
     - 비교 잎 가운데 checkout의 03_src·02_params 파일 sha를 담은 것은 1뿐이다.
     - 경로 1 `h6_L1_reference.json :: meta.c2_py_sha256`은 저장 입력 `h8_noise_VB.json`의 `meta`를 옮긴 값이라 TA와 무관하므로 빼지 않는다(rev26 여섯 번째 재감사 W-n).
  2. 경로 1 `head_check.json`(두 폴더)과 경로 2 `harness.json :: head_check`. 대신 기대값으로 본다.
     - `head` = `expected_head` = TA
     - `src_params_changed` = `allowed_src_changes.txt`(3.1절 대체 조건 2)의 목록
     - 경로 1 `markers` = `[]`, `exit_code` = 0, 경로 2 `ok` = 참
  3. 인자 목록 원소 `--allowed-src-changes`와 바로 다음 원소
- 도구 판 블록(`diff_vs_existing`, `definition_changes`, `imports.*_sha256`, `common_sha256`, 도구 sha)은 rev26 부록 A의 S 범주로 이미 빠진다.

### 3.1 TA 정의, 허용 집합, RD-1 4·5 대체 조건 (수정 11, 확인 필요 1, G-b)

**사실**(2026-11-28 git 확인. 내용은 열지 않고 이름만 봤다. 경로 2 폴더는 개수만 셌다)
- T26′는 M4 위 단일 커밋이다.
  - M4 대비 37파일: `.gitattributes` 1, `04_scripts` 3, `05_tests` 3, `06_analysis` 30
  - 03_src·02_params 변경은 0이다.
- H_I 후보 `b0416724`는 M4의 후손이다(M4 → `976aa771` → v5-imua). M4 대비 2,787파일이다.
  - `03_src` 14, `04_scripts` 56, `05_tests` 42, `06_analysis` 2,668, `00_docs` 4, `.claude` 1, `CLAUDE.md` 1, `.gitattributes` 1
  - 경로 2 폴더(`path2/`·`path2_v5c/`) 변경은 0이다.
- 두 쪽이 모두 바꾼 파일은 둘이다: `.gitattributes`와 `04_scripts/04_hydraulic/coupled/judge4368_common.py`.
  - 시험 병합(`git merge-tree --write-tree --name-only 74c27846 b0416724`, 객체만 씀, 참조 없음)에서 충돌은 `.gitattributes` 1개였다.
  - `judge4368_common.py`는 자동 병합됐다.
- `git diff --name-only R2..M4 -- 03_src 02_params`는 비어 있다. 그러므로 `R2..TA`의 03_src·02_params 변경은 `M4..H_I`의 그것과 같다. 지금 14파일이다.
  - 판 5 코드(M4 → `976aa771`): `control/c2.py`, `control/extend_start_bound.py`, `control/two_pressure.py`, `hydraulics/check_open_delay.py`, `hydraulics/rod_release.py`, `hydraulics/v5_options.py`
  - A형(`976aa771` → `b0416724`): `control/c2.py`, `control/ground_contact.py`, `control/imu_outputs.py`, `control/standstill.py`, `hydraulics/v5_options.py`, `sensors/__init__.py`, `sensors/attitude.py`, `sensors/attitude_only.py`, `sensors/suite.py`, `signals.py`(모두 `03_src/outrigger_sim/` 아래)
- H_I 쪽이 바꾼 436.8 경로 1 판정·재생 파일(M4 → `b0416724`, 이름만): `chrono_rows_judge_4368.py`, `v5_resume_4368_chrono_rows.py`, `chrono_t45_replay.py`, `h6_judge_4368.py`, `h8_noise_judge_4368.py`, `judge4368_common.py`, `t4h_replay.py`. 실행 쪽 `verdict_runs.py`·`s9_batch.py`도 있다.
  - Chrono C-5 등급기 `chrono_bundle_grade_4368.py`는 R3f → M4 사이에 바뀌었다.
  - 경로 2 폴더는 R3f → M4 사이에 15파일, M4 → T26′ 사이에 13파일 바뀌었다.
- 수정 10 3.1 1항("`T26..TA` ⊆ 허용 집합 = 갈고리·판정 모드·시험")은 위 판 5 코드와 master 쪽 판정 도구 변경 때문에 **문언 그대로는 충족할 수 없다**. 아래로 바꾼다.

**TA 조립**(메인이 한다. 각 단계의 명령·시각·결과를 `ta_identity.json`에 적는다)
1. **H_I 고정**: A형 실행 코드가 모두 들어간 v5-imua 커밋을 H_I로 정한다. 그 뒤 실행 코드를 바꾸면 새 H_I가 되고, 아래 2~5를 처음부터 다시 한다(J-2·J-2c 포함, 앞 결과는 공개).
2. **TA0** = `git -C <저장소> worktree add .claude\worktrees\imua-ta -b imua-ta 74c27846` 다음 `git merge --no-ff <H_I>`. 첫 부모는 T26′, 둘째 부모는 H_I다.
   - 충돌은 `.gitattributes`에만 허용한다. 해결 = T26′ 판의 줄을 그 순서대로 두고, H_I 판에만 있는 줄을 H_I 순서대로 끝에 덧붙인다. 같은 줄은 한 번만 두고, 다른 줄은 넣지 않는다.
   - 그 밖의 파일에서 충돌이 나면 TA0을 만들지 않고 멈춘다(확인 필요로 올림).
   - 자동 병합 파일은 git 결과 그대로 두고 손대지 않는다.
3. **P1A·P2A**: 경로 1·경로 2 작성자(3.3절)가 각각 TA0에서 브랜치 `imua-ta-p1`·`imua-ta-p2`를 따서 커밋 하나씩 만든다.
4. **TA** = TA0 위 단일 커밋 하나다. 트리 = TA0 트리 + P1A 변경 + P2A 변경이다. 커밋 메시지는 T26·T26′ 꼴로 "path 1 (P1A 해시) + path 2 (P2A 해시)"를 쓴다.
5. TA worktree(`.claude\worktrees\imua-ta`, HEAD = TA)에 `git worktree lock`을 걸고 `core.autocrlf=true`로 둔다.

**A형 허용 집합** `ta_allowed_changes.tsv`(메인이 TA 조립 뒤 기계적으로 만든다)
- 꼴: UTF-8, LF, 탭 구분. 열은 `path`, `side`, `category`, `evidence`다.
- 줄 = `git diff --name-only T26′..TA`의 각 파일이다. 정렬하고, 줄 수를 머리에 적는다.
- `side`(닫힌 목록)

| side | 뜻 | blob 규칙 |
|---|---|---|
| `I` | H_I 쪽에서만 바뀜 | `git show TA:<f>` blob id = `git show H_I:<f>` blob id |
| `M` | 두 쪽 모두 바뀜(`.gitattributes`, 자동 병합 파일) | `.gitattributes`는 위 줄 합집합 규칙. 자동 병합 파일은 TA blob = `git merge-tree --write-tree T26′ H_I` 결과 트리의 blob |
| `P1` / `P2` | P1A / P2A가 바꿈 | TA blob = P1A / P2A blob. `M`·`I` 파일을 P1A가 고쳤으면 `P1`로 적고 원래 side를 비고에 남긴다 |

- `category`(닫힌 목록)와 요구 근거

| category | 대상 | `evidence`에 적을 것(파일마다) |
|---|---|---|
| `src` | 03_src·02_params | (i) 기본 경로 비트 동일 시험의 pytest node id(TA에서 통과, skip 0. 옵션 뒤에만 닿는 변경(판 5 4파일 등)은 옵션을 끈 명령이 같은지 확인하는 시험). (ii) 정체성 관문 I-H·I-C(3절, 전체 근거). (iii) 판정 import 닫힘에 들면 J-2·J-2c 가운데 해당하는 것 |
| `judge` | 판정 import 닫힘(`ta_closure.json`) 안의 `04_scripts`·`verif_matrix/scripts`·경로 2 폴더 파일 | 하네스 판정 닫힘이면 J-2, Chrono C-5 판정 닫힘이면 J-2c(둘 다면 둘 다) |
| `exec` | A형 실행 닫힘 안이고 판정 닫힘 밖인 `04_scripts` | 기본값 스모크 `commands_sha256` 같음(구현 보고 3절 9런 꼴, RA에서 다시) + I-H |
| `tool_other` | 두 닫힘 모두 밖인 `04_scripts`(판 5·J-P3 도구, `imua_check*` 등) | 닫힘 밖임(`ta_closure.json` 항목) |
| `test` | `05_tests` | 닫힘 밖임 |
| `data_doc` | `06_analysis`·`00_docs`·`.claude`·`CLAUDE.md` 등 코드가 아닌 것 | rev26 2절 W의 추적 자료 목록 밖임. W 안이면 `data_doc_w`로 적고 J-2(+J-2c)를 근거로 한다. 지금 후보에서 W 패턴에 걸리는 것은 `verif_matrix/v5_resume_4368_harness_judgement.md`·`v5_resume_4368_judgement.md` 2개다(판정서, 봉인 확인 대상 규칙 파일 아님) |
| `attr` | `.gitattributes` | 3.2절 줄바꿈 점검 |

- **판정 import 닫힘**: 경로 1 판정 실행본(J-2·J-2c·A형)이 부르는 진입 스크립트와, 경로 2 도구 폴더 진입 스크립트에서 출발한 정적 import 닫힘이다. 실행 시 읽는 도구 스크립트도 포함한다(rev26 W 표: `r79_sensor_judge.py`, `cmd_openloop` 등).
- **A형 실행 닫힘**: 2.1절 명령의 진입 스크립트(`run_v5.py`, 화면 4개, Chrono `run_S8C`·`run_S9`·`s9_batch.py`)에서 출발한 정적 import 닫힘이다.
- 두 닫힘은 메인이 경로를 가리지 않는 기계 도구로 TA에서 만든다(도구와 sha는 10절 칸). 결과 `ta_closure.json`을 고정한다. 경로 작성자는 이 일을 하지 않는다.

**RD-1 4 대체 조건**: 메인이 A형 판정 전에 git으로 확인하고 `ta_identity.json`에 기록한다.
1. `ta_allowed_changes.tsv`의 `path` 집합 = `git diff --name-only T26′..TA`(**같음**, 줄 수 포함). 각 줄의 `side` blob 규칙이 성립한다. 모든 줄에 `category`와 그 category가 요구하는 `evidence`가 있다.
2. `git diff --name-only R2..TA -- 03_src 02_params` = `category = src` 줄 집합(같음). 이 목록을 `allowed_src_changes.txt`로 고정해 `--allowed-src-changes`에 준다.
   - 꼴: UTF-8, LF, 한 줄에 저장소 상대 POSIX 경로 하나, 사전순 정렬, 빈 줄 없음, 끝 LF
   - 지금 후보에서는 14줄이다.
3. P1A·P2A의 변경 파일 집합이 서로 겹치지 않는다. 03_src·02_params와 A형 실행 닫힘 파일을 포함하지 않는다. `git diff --name-only RA..TA -- 03_src 02_params`가 비어 있다.
   - 수정 10 3.2 끝의 "RA ⊆ TA의 03_src 변경 집합"을 이 조건으로 바꾼다. 실행 코드와 판정 코드가 같은 03_src(태그 술어 포함)를 쓴다.
4. J-2 통과(3.2절)
5. J-2c 통과(3.4절). J-2c가 불일치면 C-5만 판정하지 않는다(6절).
6. rev26 2절 W의 규칙 파일과 추적 자료 가운데 TA에서 blob이 T26′과 다른 것이 `category = data_doc_w` 줄과 같다. 봉인 확인 대상 규칙 파일(rev26 부록 A의 34개, rev26 원판·정오 1~3과 `.sha256`) 가운데 바뀐 것은 0이다.

**RD-1 5 대체**
- A형 판정, J-2, J-2c는 HEAD = TA인 TA worktree에서 돈다.
- head-check는 `--allowed-src-changes allowed_src_changes.txt`로 준 목록만 허용 변경으로 받는다. A형 판정(`--tag-mode imua`), J-2·J-2c(436.8 모드)에 같은 목록 파일을 준다.
- T26′ 재판정(rev26 5단계)은 끝났고 다시 하지 않는다.
- 경로 2 실행본 자체의 PowerShell 관문(`Test-CheckoutState`)에는 도구 인자가 닿지 않는다. 그래서 A형 판정·J-2·J-2c 실행본 모두 3.2절 3번처럼 고쳐, 대체 조건 2의 목록과 같은지 본다.

### 3.2 J-2 실행본 (rev26 5단계 2회차 실행본 + 아래 변경, 이것뿐)

- 기준
  - rev26 정오 3의 두 2회차 실행본 `v5_resume_4368/rev26_run2/run_judgement_path1_rev26b.ps1`·`run_judgement_path2_rev26b.ps1`(정체성 `rev26_run2/t26b_identity.json`)
  - 비교 기준 출력은 `v5_resume_4368/judge_rev26_74c2784/{harness_path1,harness_path2}/`와 비교기 출력 `rev26_stage5_run2/compare_r4_rev26b.json`이다(정체성 정본 `rev26_stage5_run2/stage5_record.json`).
- 바꾸는 줄(줄 번호는 J-2 실행본을 쓸 때 2회차 실행본 기준으로 고정한다)
  1. 기대 HEAD·비교 커밋(경로 1 `$M4`·`$R4`, 경로 2 `$M4`·`$R4`): T26′ → TA
  2. worktree → `C:\workspace\outrigger_control\.claude\worktrees\imua-ta`(3.1절 5)
     - 경로 1 `$Judge`·`$Co`가 이 경로를 가리킨다.
     - 경로 2는 `$WT`(→ `Set-Location`·`$P2`·`$V5c`)가 이 경로를 가리킨다.
  3. 경로 2 관문 `Test-CheckoutState`의 03_src 확인: "`git diff --name-only $R2..$M4 -- 03_src 02_params`가 비어 있음" → "그 목록이 `allowed_src_changes.txt`와 같음"
  4. 경로 2 `$AllowListPath2` → TA blob 값(`git show TA:<파일>` raw 바이트 sha256)
  5. 두 경로에서 head-check를 하는 호출(경로 1 `head-check`, 경로 2에서 `--expect-head`를 받는 단계)에 `--allowed-src-changes <allowed_src_changes.txt>`를 더한다.
  6. 출력 폴더 줄 → `v5_resume_4368/judge_j2_<TA7>/{harness_path1,harness_path2}`
- 그대로 두는 것
  - cwd·입력 루트(메인 checkout)
  - 입력 기준 인자: 경로 2 `--data-root $Repo` 9개 호출, 경로 1 h11 `--las-k1-dir 06_analysis/02_control/v5_rerun/las_k1`·family_table `--data-root .`(rev26 2절)
  - 인터프리터, 그 밖의 줄
- **통과 조건**(모두)
  - (가) rev26 부록 A 규범 규칙 **r6**(`rev26_e2_fixed/excl_fields_r6.py`, sha `ce5208a8…`, 각 쪽 자기 인자)에 3절 J-2 제외 셋을 더해 비교했을 때 diff 0
  - (나) 종료 코드가 2회차와 같다(경로 1 = 1, 경로 2 = 0)
  - (다) 비교기 `compare_r4.py`(sha `8ff3d32b…`)를 2회차와 같은 인자로, 폴더만 바꿔 돌린 결과가 `compare_r4_rev26b.json`과 같다(같은 2항목). 시각·폴더 토큰은 r6 I·NT 규칙으로 뺀다.
  - 다르면 TA의 변경이 436.8 판정에 효과가 있다는 뜻이다. 설정 결함으로 보고 A형 묶음을 시작하지 않는다.
- **J-2는 TA 커밋당 1회**다. 다시 하려면 TA를 새로 고정하고, 그 사실과 앞 결과를 공개한다. **J-2 출력은 rev26 낱말로 쓰지 않는다.**
- `ta_identity.json`에 고정할 것
  - TA·TA0·P1A·P2A·H_I 전체 해시, TA0 병합 해결 기록(`.gitattributes` 줄 합집합 diff)
  - `ta_allowed_changes.tsv`·`allowed_src_changes.txt`·`ta_closure.json`과 각 sha
  - J-2·J-2c 실행본 sha와 기준 실행본 대비 diff, `$AllowListPath2` 표
  - worktree 경로와 `core.autocrlf`
  - 외부 도구·환경(rev26 `t26b_identity.json`과 같은 항목)
  - 입력 기준 표와 TA 구현 기록의 대조(TA가 더한 site 포함)
- **TA worktree 깨끗함(W-i)**
  - 메인이 J-2, J-2c, A형 판정 실행 각각의 시작 직전과 끝난 직후에 `git -C <TA worktree> status --porcelain`(추적·비추적 모두)이 비어 있는지 본다.
  - 명령·시각·출력을 `ta_identity.json`의 `wt_status_before`·`wt_status_after`(실행별)에 적는다.
  - 시작 전에 비어 있지 않으면 시작하지 않는다. 끝난 뒤라면 설정 결함으로 보고한다.
- J-2 전에 verif가 할 점검
  - 실행본: `ps1_lint.py` 종료 0, diff가 위 변경뿐
  - `.gitattributes`·줄바꿈
    - TA worktree에서 rev26 4′ W-l 대상 4개 파일(rev26 `.md`·`.sha256`·`excl_fields_r5.py`·`rev26_excluded_fields_r5.json`)과 정오 2의 r6 파일이 `unset`·`w/lf`인지 본다. 폐기본은 `unset`만 본다.
    - `git diff T26′..TA -- .gitattributes`의 더한 줄 = (`git diff M4..H_I -- .gitattributes`의 + 줄) ∪ (A형 규칙 파일 `-text` 줄)이고, 지운 줄은 0이어야 한다.
  - 입력 기준 점검(TA 코드 기준)
  - 줄바꿈 잎 점검: TA worktree `v5_options.py` raw sha = TA blob의 CRLF 꼴 sha. 이 잎은 J-2 제외 1로 빠지므로 기록만 한다.
- J-2 비교의 새 출력 쪽 인자
  - 커밋 TA, 출력 토큰 `judge_j2_<TA7>`, J-2 실행 창
  - `--main-root C:\workspace\outrigger_control --checkout-root <TA worktree>`
  - `--allowed-src-changes`·`--data-root` 쌍은 r6 규칙이 인자 목록에서 이미 뺀다.

### 3.3 TA 작성 명세 (경로별 새 인스턴스 2개, 수정 11, 확인 필요 1·7)

- **작성자 조건**
  - 경로 1·경로 2를 각각 새 python-expert 인스턴스가 쓴다. 두 인스턴스는 436.8 H-3·H-4·C-5 출력과 판정 후 감사의 해당 줄, A형 실행 출력을 읽지 않은 인스턴스여야 한다.
  - P-2·P-5~P-8 구현 인스턴스(구현 보고 `impl_resume_20261128.md` 작성자)는 두 경로 어느 쪽도 맡지 않는다. 그 인스턴스는 경로 1 C-5 판정기를 열었고 A형 확인 실행 기록을 읽었기 때문이다(구현 보고 6절 1).
  - 두 작성자는 서로의 코드·출력·브랜치를 열지 않는다. 같은 정의는 3.3.1 문장만으로 각자 맞춘다.
- **보완 한 번 = P1A 하나 + P2A 하나.** 개발 시험은 합성 고정물로만 한다. 판정 도구를 436.8 저장 결과와 A형 출력에 돌리지 않는다(J-2·J-2c·A형 판정은 메인이 1회씩 한다).
- 구현 기록(각자 자기 경로 행만): 근거 정의 문장(이 문서 절·[정의] 번호), 바뀐 하위 명령 표, 입력 경로 기준 표(rev26 3절 꼴), 모드별 동작 표

#### 3.3.1 공통 [정의] 블록 (두 작성자에게 글자 그대로 넘긴다)

- **[정의 A-1] 태그 모드**
  - 실행 인자 `--tag-mode {4368,imua}`(T26′에 있는 인자)에 값 `imua`의 동작을 더한다. 기본값은 `4368`이고 그 동작은 바꾸지 않는다.
  - `imua`일 때 기대 태그는 다음과 같다.
    - D-1·U-3: V0 → `final_C4G2_LAS_K1_IMUA`, VB → `final_C4G2_P3_LAS_K1_IMUA`
    - U-6: C2 → `final_C4G2_P3_LAS_K1_IMUA`, ABL → `ABL_LAS_K1_IMUA`, IND → `IND_IMUA`, IND_LAS → `IND_LAS_IMUA`
    - C-5: 행 설정 V0·VB에 따라 앞의 두 문자열
  - U-6은 rev26 R26-3의 두 필드 읽기 규칙 그대로다(`records[].controller`와 `records[].v5.controller_tag`, 대응 문자열과 그대로 같을 때만 통과).
  - 그 밖은 S-2다. 접미사를 떼는 술어는 쓰지 않는다(③ 판별 제외). 모드는 출력에 새 키로 적지 않는다.
- **[정의 A-2] `imu_sensor` 블록**
  - `imua` 모드에서 판정 줄·행마다 `imu_sensor` 블록을 읽는다. 위치는 D-1 줄 최상위 `imu_sensor`, U-3·U-6 레코드 `v5.imu_sensor`, Chrono `result.json :: controller_meta.imu_sensor`다.
  - 봉인 파일 `v5paper_imua/imua_expected_imu_sensor.json`의 칸과 비교한다. C2·ABL 하네스는 `harness_c2`, IND·IND_LAS는 `harness_ind`, Chrono는 `chrono_c2`다.
  - JSON 값끼리 같아야 한다(키 집합과 값 모두). 없거나 다르면 S-2다.
  - `4368` 모드에서는 읽지 않는다.
- **[정의 A-3] 판정 행 수**
  - `imua` 모드의 판정 행 수는 H-1 868, H-3 2,228, H-4 726(IND_LAS 기록 242는 따로), C-5 35다. 다르면 설정 결함이다.
  - 판정 행이 0이면 판정 불가다(통과 아님).
- **[정의 A-4] 묶음 범위**
  - `imua` 모드가 내는 묶음은 H-1(줄 결과만, 묶음 낱말 없음), H-3, H-4(+ IND_LAS 기록), C-5뿐이다.
  - 다른 묶음의 칸은 만들지 않는다. 묶음을 모으는 하위 명령(목록·종합)은 이 네 묶음만 모은다. 종합 최악값은 H-3·H-4·C-5로만 낸다.
  - 네 묶음 가운데 입력이 없는 것은 판정 불가다.
- **[정의 A-5] `--allowed-src-changes <파일>`**
  - 파일 꼴: UTF-8, LF, 한 줄에 저장소 상대 POSIX 경로 하나, 사전순 정렬, 빈 줄 없음, 끝 LF
  - HEAD·03_src를 확인하는 하위 명령은 03_src·02_params 변경 집합이 이 목록과 **정확히 같을** 때만 그 변경을 허용한다. 목록 밖 변경이 있거나, 목록에 있는데 바뀌지 않았으면 기존 멈춤과 같은 표지를 낸다.
  - 인자가 없으면 기존 동작(허용 없음)이다.
  - 03_src 변경을 보지 않는 도구는 이 인자를 받아 기록만 하고, 파서에서 거부하지 않는다.
- **[정의 A-6] 입력 기준**: T26′ 그대로다(경로 2 `--data-root`, 경로 1 실행본 인자). A형 입력도 같은 기준을 따른다. 도구 저장소에서는 rev26 2절 W만 읽는다.
- **[정의 A-7] C-5 T4/T5의 A형 행**
  - A형 행(기대 태그와 `imu_sensor` 블록이 둘 다 있는 행)도 436.8 정의 그대로 판정한다. 행에 기록된 실행 설정으로 감시기 설정을 다시 만들고, 대체 없이 재생한 하한이 실행 기록 하한과 같을 때(상대 1e-12)만 T4/T5를 판정한다. 같지 않으면 판정 불가다.
  - A형 행의 실행 설정 = 기록된 436.8 설정에 1절 A형 설정(자세만 출력, 탐침 자세 단서 끔, D1′ `explained`, `v5_A` 게인)을 **마지막에** 적용한 것이다.
  - 태그와 블록 가운데 하나만 있거나, 블록이 [정의 A-2]와 다르거나, 프리셋과 게인이 다르면 재생하지 않고 S-2다.
- **[정의 A-8] 문턱**: 새 문턱은 없다. 436.8·rev26 정의와 문턱 비교 규칙을 그대로 쓴다.

#### 3.3.2 경로 1 작성자(P1A)만

- 대상
  - `resume4368_judge.py` head-check와, `--expect-head`를 받는 경로 1 판정 스크립트 전부: [정의 A-5]
  - 태그를 판정하는 경로 1 하위 명령 전부(하네스 H-1·H-3·H-4, Chrono C-5 등급기): [정의 A-1]~[A-4]
- C-5 재생
  - H_I에 이미 있는 경로 1 재생기(P-8)는 다시 쓰지 않는다.
  - C-5 등급기가 A형 행을 그 재생 경로로 넘기는지 확인하고 구현 기록에 파일:행으로 적는다.
  - 고칠 곳이 재생기 안이면 P1A가 아니라 H_I 쪽 수정으로 한다(새 H_I → 3.1절 TA 조립을 처음부터).
- H-12 하네스 T4h 재생은 `imua` 모드에서 부르지 않는다. `_IMUA` 거부 동작은 바꾸지 않는다.
- 4.4 분류 대응 입력: `imua` 모드 출력의 판정 항목 이름 목록(묶음별)을 구현 기록에 표로 낸다. P-7이 이 표로 관문 ID 상수를 고정한다.
- 바꾸지 않는 것: 03_src·02_params, A형 실행 닫힘 파일, 경로 2 폴더(열지도 않는다)

#### 3.3.3 경로 2 작성자(P2A)만

- 대상: 경로 2 폴더(`path2/`·`path2_v5c/`) 도구 가운데 태그를 판정하거나 HEAD를 확인하는 것 전부. 앞쪽은 [정의 A-1]~[A-4], 뒤쪽은 [정의 A-5]를 적용한다.
- [정의 A-5]: 경로 2 도구는 HEAD만 본다. 인자를 받아 기록만 한다. 03_src 확인은 실행본 관문(3.2절 3번)이 맡는다.
- C-5 T4/T5([정의 A-7], 확인 필요 7)
  - 경로 2가 T4/T5 재생을 자기 코드로 하는지, 저장소의 원 판정기를 부르는지 **자기 코드에서** 확인하고 구현 기록에 적는다.
  - 자기 코드라면: A형 행을 거부하거나 A형 설정을 다시 만들지 못할 때 [정의 A-7]대로 고친다.
  - 원 판정기를 부른다면: 그 호출(명령·인자)만 적고 그 판정기 코드는 열지 않는다. 436.8 결정 90 (4)의 "경로 2의 원 판정기 직접 실행 허용과 독립성 공개" 꼴로 공개한다. 이때 [정의 A-7]의 동일성은 원 판정기 결과로 본다고 적는다.
- 바꾸지 않는 것: 03_src·02_params·04_scripts

#### 3.3.4 넘김과 넘김 금지

- 경로 1 작성자에게 넘기는 것: 3.3.1 + 3.3.2 + 1절 기대 태그 표 + 1.1절 + 2.2절 표 + 3.1절 "TA 조립" 3. 봉인본에서 글자 그대로 뽑고, 출처(파일·sha·행)를 붙인다.
- 경로 2 작성자에게 넘기는 것: 3.3.1 + 3.3.3 + 같은 표들 + 3.1절 "TA 조립" 3. 넘기는 방식은 경로 1과 같다.
- **경로 2 넘김 금지**
  - 경로 1 코드·출력·브랜치(`imua-ta-p1`)·blob, 감사 보고가 인용한 경로 1 줄
  - 이 문서의 3.3.2
  - 판정 전 점검·구현 보고 폴더(`imu_attitude_only/imua_seal_prep/`의 `impl_*`·`report.md`, P1A 구현 기록)
  - 실행 출력 sha 목록·백업, 러너 사본
- **경로 1 넘김 금지**: 대칭이다. 경로 2 코드·출력·브랜치(`imua-ta-p2`)·blob, 3.3.3, P2A 구현 기록
- 넘김 전에 `handoff_leak.py`로 상대 경로 이름 누설과 공통 블록 sha를 본다.

### 3.4 J-2c: TA의 436.8 모드 Chrono C-5 동일성 (수정 11, 요청 밖 추가 1, G-g)

- **이유**: J-2는 하네스 판정 도구만 다시 돌린다(rev26 5단계 범위). C-5 Chrono 판정 도구는 436.8에서 R3f `8a0c843`으로 판정됐다. 그 뒤 다음이 바뀌었다(3.1절 사실).
  - 경로 1: `chrono_bundle_grade_4368.py`(R3f → M4), `chrono_rows_judge_4368.py`·`v5_resume_4368_chrono_rows.py`·`chrono_t45_replay.py`(M4 → H_I)
  - 경로 2 폴더: R3f → T26′ 사이 변경 있음
  - J-2만으로는 A형 C-5 판정 도구의 436.8 모드 동일성 근거가 없다.
- **정의**: TA worktree에서 두 경로 Chrono 판정을 436.8 모드(`--tag-mode` 없음)로, 436.8 저장 Chrono 행(R2 실행분)에 1회 돌린다. 범위는 R3f 판정과 같은 64행이다. R3f 출력 `v5_resume_4368/judge_8a0c843/{chrono_path1,chrono_path2}/`와 비교한다.
- **J-2c 실행본** = R3f 두 경로 Chrono 실행본 + 아래 변경(이것뿐)
  - 기대 HEAD·비교 커밋 → TA
  - 도구 위치 → TA worktree
  - 경로 2 03_src 관문 → `allowed_src_changes.txt`와 같음
  - head-check 호출에 `--allowed-src-changes`
  - 출력 → `judge_j2c_<TA7>/`
  - **t45 재생 출력은 재사용하지 않고 TA에서 다시 만든다**(재생기가 바뀌었으므로)
  - R3c 러너 판정 출력(`judge_f9bc3c7\chrono_path1\runner_judge\`)은 R3f와 같이 sha 대조 뒤 재사용한다
  - R3f 실행본 경로·sha와 diff는 10절 칸이다.
- **통과 조건**
  - rev26 부록 A r6의 범주 정의(I·S·F 제외, NT·NM 정규화)를 Chrono 출력에 적용하고, J-2 제외 셋에 해당하는 Chrono 출력 필드를 더 뺀 뒤 diff 0
  - 종료 코드·멈춤 표지(경로 2 C-5 CD-7 멈춤 포함)가 R3f와 같다
  - Chrono 출력의 제외 필드 열거 `j2c_excluded_fields.json`은 봉인 전에 control-expert가 R3f 출력의 **키 이름 목록만**(값 열람 없음)과 TA 변경 파일 목록으로 만든다(10절 칸).
- J-2c는 TA 커밋당 1회다. 출력은 436.8 판정 낱말로 쓰지 않는다. 판정 도구가 436.8 저장 결과에 돈 횟수로 세어 공개한다.
- 불일치면 C-5 A형 판정을 하지 않는다(설정 결함). 하네스 묶음은 J-2 기준으로 진행할 수 있다(6절). C-5 본 실행(Chrono 55~150 스레드·h) 전에 J-2c를 끝낸다.

### 3.5 A형 판정 실행본 (수정 11, 요청 밖 추가 5, 빈칸 있음)

- 하네스: J-2 실행본 + 다음 변경
  - (a) 판정 하위 명령에 `--tag-mode imua`
  - (b) 입력 변수 → 2.1절 A형 결과 위치
  - (c) [정의 A-4] 밖 묶음의 하위 명령을 부르지 않음(부르는 하위 명령 목록을 고정)
  - (d) 출력 → `v5paper_imua/judge_<TA7>/{harness_path1,harness_path2}`
- Chrono: J-2c 실행본 + 같은 꼴의 변경. 범위는 C-5 35행이고, 출력은 `…/judge_<TA7>/{chrono_path1,chrono_path2}`다.
- 두 실행본의 줄 diff와 sha, 부르는 하위 명령 목록은 10절 칸이다. verif가 실행 전에 `ps1_lint.py`와 diff를 점검한다.
- 판정은 J-2·J-2c 통과 뒤, A형 본 실행이 끝난 뒤에 메인이 1회 한다.

**정체성 관문**(어긋나면 설정 결함, 판정하지 않음)
1. I-H 50줄 선정
   - 경로 칸(묶음 × 설정 × D-1 계열 11 / U-3 연구 9 / U-6 제어기 4)마다 먼저 1줄씩 뽑는다. 44칸이다: D-1 22, U-3 18, U-6 4(IND_LAS 포함).
   - 남은 6줄은 시드 20261114 단순 무작위로 뽑는다.
   - 키당 ε 하나만 뽑는다.
   - 목록은 실행 전에 sha로 고정한다. 구현은 `imua_identity_sample.py`이고 모집단은 4,064줄이다. RA에서 다시 만든다.
   - D-1 줄은 `run_v5 d1` 키 부분집합 인자(P-7)로 돌린다.
2. I-H 50줄과 I-C 2행의 `commands_sha256`이 436.8 저장 줄·행과 모두 같아야 한다.
3. R2와 RA 사이 03_src·02_params diff 목록 = `allowed_src_changes.txt`(3.1절 대체 조건 2)
   - 파일마다 `ta_allowed_changes.tsv`의 `src` 근거(기본 경로 비트 동일 시험)가 있어야 한다.
   - 제어기·플랜트·하네스 경로의 04_scripts 차이는 `exec` 근거가 있어야 한다.
4. 검출력 공개
   - 무작위 50줄은 바뀐 줄이 전체의 5.8 % 이상일 때 95 %로 잡는다.
   - 칸 층화는 칸 단위 경로 변경을 잡는다.
   - 드문 분기(③·대체 다리)만 건드리는 변경은 표본으로 잡지 못한다. 3항의 파일별 근거가 이를 맡는다.

## 4. 판정과 예상 한계 목록

### 4.1 판정

- 묶음마다 TA 두 경로 판정 도구(`imua` 모드), 436.8과 같은 문턱, 같은 묶음 등급 대조 표로 판정한다.
- **상태 순서: 실행 오류(6절) > 설정 결함(3절) > 판정 불가 > 미달 > 통과.**
  - 기록 묶음(IND_LAS 열 등)은 `기록 완료` / `기록 불완전`이다.
  - 2.2절 A형 기록 실패는 기록 실패다. 닫힌 목록은 다음 셋뿐이다: 기록 파일 없음, 기록 태그 불일치, 2.2절 키 없음. 판정 상태를 바꾸지 않고 수만 적는다.
- 각 묶음은 적용 행 수, 판정 행 수, 판정 불가 행 수를 기록한다. **판정 행이 0이면 판정 불가다(통과 아님).**
- H-1(D-1)은 436.8에서도 묶음 낱말을 내지 않았다(등급 대조 표 102행 "한정"). A형 D-1의 정보는 R-10 줄 전이와 4.2 분류뿐이다.
- IND_LAS 표지로 생긴 경로 1 H-4 `판정 불가`는 rev26 1.2대로 S-13으로 세지 않는다(rev26 0절: 결과 뒤에 넣은 예외).
- **축소안 밖 묶음**([정의 A-4])은 종합에 넣지 않는다. 판정서에는 "축소안 밖(돌리지 않음)"으로 적는다. 판정 불가로 세지 않는다.
- **C-5 경로 2 CD-7**(요청 밖 추가 3)
  - 436.8 결정 107 (2)는 "H-9: M2 끔이라 해당 없음, CD-1 목록 밖 기록 항목"을 적고 도구는 고치지 않은 채 행 등급으로 낸다는 처리였다. 경로 2 C-5가 같은 CD-7 빈 사유로 멈추면 이 처리를 그 문장 그대로 적용한다. 결과 전에 고정하는 처리다.
  - 다른 사유의 멈춤은 436.8 원판 13절 2항대로 사용자가 결정한다.
- 4.2 목록은 **판정 낱말을 바꾸지 않는다.** 판정서에는 해석 열만 더한다.
- 4.2 분류는 경로 1 판정 출력의 항목 이름으로 한다(3.3.2 "4.4 분류 대응 입력"). 두 경로 등급이 갈린 줄(S-13)은 분류하지 않고 "짝 판정 불가"와 따로 센다.

### 4.2 결과 전 공개: A형 한계로 예상되는 등급 악화 (해석 보조)

- 대상 줄: 436.8 짝 대비 등급이 나빠진 줄(통과 → FLAG·안전 종료·미달, FLAG → 미달). E-1은 READY 시각이 줄 한계(4.3)를 넘은 줄도 포함한다.
- "설명됨"은 다섯 조건을 모두 만족할 때만이다.
  1. 같은 키의 436.8 짝(H-3·H-4는 rev26 재판정 뒤)이 그 항목을 통과했다.
  2. 실패 항목이 E 항목의 관문 종류에 속한다(관문 ID는 4.4).
  3. 기록에 E 항목의 기전 서명이 있다(아래 수치 문턱, E-2 계산 정의는 4.2.1).
  4. 크기 상한 안이다.
     - E-1: A − 436.8 짝 첫 READY 지연 ≤ 30 s(V0)·45 s(VB)
     - E-4: A − 짝 복귀 시간 차 ≤ U_E4 = 16.9 s(`imua_check_judgement_rev2.json` G4 행의 A-v5 − R0 E5 최대, R3 ε 0·1e-3)
  5. 기회 집합 안이다(E-2만).
- 하나라도 빠지면 "A형 미달, 설명 안 됨"이다. 사유별로 센다: 짝 미통과, 관문 밖, 서명 없음, 서명 평가 불가(배열 없음), 예상 크기 초과, 기회 밖.
- 436.8 짝이 판정 불가·멈춤·READY 없음이면 "짝 판정 불가"로 따로 센다.
- 분류는 봉인 때 sha로 고정한 분류 스크립트(P-7)가 기록 필드만으로 한다. 사람 판단은 넣지 않는다.
- 특이도 공개: E 항목마다 등급이 나빠지지 않은 줄에서 서명이 성립하는 비율을 함께 적는다.

| # | 예상 한계 | 관문 종류 | 기전 서명(수치 문턱, 모두 성립) | 근거 |
|---|---|---|---|---|
| E-1 | READY 지연 | READY 시각 한계(4.3) | (i) A 첫 READY > 줄 한계 ≥ 436.8 짝 첫 READY, (ii) 지연 ≤ 조건 4 상한 | A − R0 중앙값 +14~16 s, VB 연약 +27~45 s |
| E-2 | READY를 선언한 뒤 잃음 | 끝 단계 READY·끝 자세·READY 도달 항목 | 4.2.1절 (i)~(vi) | A2 관측: 0.6~2.1 s, 필터 0.0744~0.0776°, 탐침 변화 0.07~0.09°, 경사계 오차 ≤ 0.022°, 최소 힘 66~80 kN. P-7 대조(`b0416724`, 양성 5줄): 간격 0.6~2.1 s, 필터 0.0744~0.0776°, 탐침 변화 0.069~0.090°, 경사계 오차 ≤ 0.0153°, 최소 힘 66.3~74.1 kN. 재레벨 문턱 0.07°(`c2.py` 642행). 기록된 제어 필터는 완료 필터보다 빨라 문턱을 먼저 넘는다(9절) |
| E-3 | 경계 경사 안전 정지 | FAULT·READY 없음, 안전 종료 허용 항목 | A 줄에 `FAULT_LIFT_STROKE_LIMIT:soil:*`, A READY 없음, 436.8 짝 READY 도달 | S7(J1 왼쪽 낮음 2.86°) |
| E-4 | 포화 뒤 느린 복귀 | U-9형 E5·T4 항목 | E5 A − 짝 > 0, ≤ U_E4 | A-v5 R3 +16.9 s. 축소 묶음에는 U-9 E5 지표 줄이 없어 "해당 관문 없음"이 예상된다 |
| E-5 | READY 중 지지 변화 감시 사실상 꺼짐 | `WARN_SUPPORT_CHANGED`·I4 기대 분류 | 436.8 짝 줄에 `WARN_SUPPORT_CHANGED`(또는 I4 기대 분류 사건)가 있고 A 줄에는 없다 | 연구: READY 중 관문 열림 3~10 % |
| E-6 | 압력 계단 진단이 하중 합 규칙만 씀 | 압력 FAULT | A 줄에 `FAULT_HEAD_PRESSURE:<다리>`와 `INFO_HEAD_PRESSURE_FAULT_REASON:<다리>:D1_step`가 크롤러 이탈 확인 뒤(LEVEL 이후)에 있고, 436.8 짝 줄에는 `FAULT_HEAD_PRESSURE`가 없다. D1′ 합 규칙 비 0.5(`two_pressure.py` 165~168행) | 연구 기록 재생 3/17 |
| E-7 | 탐침 자세 단서 끔 | 접지 판정(J_P형) | — | 축소안에 J_P 없음(해당 없음 공개) |

- 기록만 하는 보조 값(서명 아님): 경사계 원 계열(`inclinometer_rad`)에 완료 필터를 오프라인으로 다시 적용한 값과 원 문턱 0.07°의 비교 결과
- **기대 건수(결과 전 고정, E-1·E-2만)**
  - E-1
    - 묶음·설정마다 436.8 짝 READY 여유(줄 한계 − 짝 첫 READY)와 확인 실행(A-v5) 지연 분포로, 기대 등급 악화 수와 97.5 % 예측 상한을 계산한다.
    - 재표집은 **확인 실행 사례 × η 집락 재표집**(B = 4,000, 시드 20261114)이다. 대상 줄의 지연은 D-1 키(ε 짝)·U-3 `cluster` 단위로 공유하고, U-3 `resample_unit` 공유를 민감도로 함께 적는다.
    - 관측된 "설명됨" E-1 수가 상한을 넘으면 "예상보다 큼"으로 공개한다(판정 낱말 불변).
    - D-1(stats 검토 1): V0 30행(95 % 20~41, **상한 41**), VB 41행(18~72, **상한 72**)
    - U-3: 4.3 규칙으로 봉인 전 계산한다(P-7, FLAG 수준).
    - U-6: READY 시각 한계 관문이 없어 해당 없음
    - C-5: 행 단위 기록만
  - E-2
    - 기회 집합은 436.8 짝의 `probe_attitude_change_deg` > 0.07°인 줄이다(D-1: V0 29줄 15키, VB 34줄 17키. 0.10° 초과는 V0 9·VB 8).
    - 짝 기록에 이 필드가 없는 묶음은 기회 집합이 "정의 안 됨"이다. 그 묶음의 E-2는 서명으로만 분류하고 "기회 미정"으로 따로 센다(기대 건수 없음).
    - 기대 수와 97.5 % 예측 상한은 A-v5의 기회 대비 사건(집락 기준)으로 봉인 전 계산한다(P-7).
  - E-3·E-5·E-6은 관측 수와 집락 수만 적는다.
- **분류 스크립트 양성·음성 대조(봉인 조건)**: P-7 분류 스크립트는 봉인 전에 RA에서 다음을 만족해야 한다. 결과(sha)는 판정서 부록에 둔다.
  - 양성: a2 확인 실행 A2의 G5b 실패 5줄(S3 VB η 0.85 ε 0·2e-3, S5 VB η 0.80 ε 1e-3·2e-3, S4 VB. T4h 자세 배열 있음) → 모두 E-2 서명 성립
  - 음성 1: 같은 실행 R0의 같은 5줄 → E-2 대상 아님(READY → LEVEL 없음)
  - 음성 2(합성 고정물 1건): 위 양성 줄 하나에 [마지막 DONE, $t_L$]의 `leg_reapproach_start` 사건을 더한 것 → E-2 서명 불성립
  - 평가 불가: A-v5 확인 실행 G5b 실패 2줄(S5 VB η 0.80 ε 2e-3·3e-3. T4h 자세 배열 없음) → "서명 평가 불가(배열 없음)"
  - 후보 결과(`b0416724`, 4.2.1 수정 2건 반영 전): 13/13 기대대로. 수정 2건을 반영한 뒤 다시 돌려 고정한다.

#### 4.2.1 E-2 계산 정의 (수정 11, 확인 필요 3)

구현(`imua_classify.py` 23~34·186~279행 @`b0416724`)이 정한 부분을 아래처럼 채택하거나 고친다. 시각은 제어 주기 표본($T_s$ = 0.1 s)의 `t_s`다. phase 값은 C2 phase 문자열(`ready`·`level`·`done`)이다. IND 기록은 `IND_PHASE_AS_C2` 대응값을 쓴다.

| 항목 | 정의 | 처리 |
|---|---|---|
| 대상 | 마지막 READY 진입 주기 $k_R$(phase가 `ready`가 된 마지막 주기) 뒤에 phase[k−1] = `ready`이고 phase[k] = `level`인 첫 주기 $k_L$. 바로 이어지는 전이만 센다. 없으면 **E-2 대상 아님** | 채택 |
| $t_R$, $t_L$ | `t_s[k_R]`, `t_s[k_L]`. "$t_L$ 표본" = READY → LEVEL 뒤 첫 LEVEL 주기 | 채택 |
| $t_D$ | $k_R$ 이전(같은 주기 포함) 마지막 DONE 진입 주기의 시각. 없으면 평가 불가 | 채택 |
| (i) | 0.3 s ≤ $t_L − t_R$ ≤ 3.0 s(양끝 1e-9 s 허용) | 채택 |
| (ii) | $k_L$ 주기 `attitude_filtered_deg`의 max(\|roll\|, \|pitch\|) ≥ 0.065°(허용 없음) | 채택 |
| (iii) | max_축 \|`attitude_true_rad`[$k_R$] − [$k_D$]\|를 도로 바꾼 값 ≥ 0.05°(허용 없음). 참 자세는 각 시각에서 가장 가까운 1 ms 플랜트 행(0.5 ms 안, 밖이면 NaN) | 채택 |
| (iv) | \|`inclinometer_t_s` − $t_L$\| ≤ 0.1 s(+1e-9 s)인 경사계 판독 전부에서 \|`inclinometer_rad` − `attitude_true_at_inclinometer_rad`\| ≤ 0.03°(축별, 허용 없음). **판독 수 $n$ = 21이어야 한다(10 ms 판독, 양끝 포함). $n$ ≠ 21이면 평가 불가** | **수정**: 구현은 판독이 1개 이상이면 평가한다. 기록 끝에 걸쳐 판독이 덜 모인 창은 평가 불가로 둔다 |
| (v) | `true_force_min_N`[$k_R$ … $k_L$](양끝 포함, 네 다리)의 최소 ≥ $F_{min}$ + 7.5 kN(16.915 kN, 허용 없음). 주기 $k$의 값은 ($t_{k−1}$, $t_k$] 최소이므로 실제 덮는 구간은 ($t_R$ − 0.1 s, $t_L$]이다 | 채택(덮는 구간 공개) |
| (vi) | [$t_R$ − 0.5 s, $t_L$ + 0.5 s]에 이름이 `relevel_predicted`·`probe_aborted_low_load`·`WARN_SUPPORT_CHANGED`·`target_changed`로 **시작하는** 사건이 없고, [$t_D$, $t_L$ + 0.5 s]에 `leg_reapproach_start`로 시작하는 사건이 없다(창 양끝 1e-9 s 포함). **$t_L$ + 0.5 s가 기록 마지막 주기 `t_s[-1]`보다 뒤면 평가 불가** | **수정**: 구현은 기록 끝 너머 창을 "사건 없음"으로 읽는다. 기록이 끝나 사건을 볼 수 없는 창이 성립으로 읽히지 않게 한다 |
| 평가 불가 | E-2 배열(`attitude_filtered_deg`, `attitude_true_rad`, `inclinometer_t_s`, `inclinometer_rad`, `attitude_true_at_inclinometer_rad`, `true_force_min_N`) 가운데 하나라도 없음, (ii)~(v)에 쓰는 값에 NaN, DONE 없음, 위 두 수정 조건. 성립·불성립 어느 쪽으로도 읽지 않는다 | 채택 |
| 기록 | $t_R$, $t_L$, $t_D$, 간격, (ii)~(v) 값, $n$, 걸린 사건 목록 | 채택 |

- 마지막 READY 진입 앞에서 READY를 잃었다가 다시 READY로 끝난 줄은 E-2 대상이 아니다. 그 줄의 악화가 시간 항목이면 E-1 쪽에서 분류된다(공개).
- 두 수정은 python이 P-7에서 반영한다(코드 수정 필요). 반영 뒤 양성·음성 대조를 다시 돌린다(양성 5줄은 기록 중간의 사건이라 두 수정에 걸리지 않을 것으로 예상하나, 확인은 재실행으로 한다).

### 4.3 줄별 READY 시각 한계 규칙 (E-1 기회·기대 건수용)

| 묶음·연구 | 줄 한계 | 436.8에서의 성격 | 근거 |
|---|---|---|---|
| D-1 | `d1.t_ready_limit_s`(줄 기록값): H-R 평지 90 / 경사 120 s, H-S 평지 100 / 경사 120 s | D-1 판정 항목(선별 여유 m_T 포함) | `d1_selection_rules.md` 58·166~167행, `d1_rows.py` 91·243~249행 |
| U-3 slope·h6·h9·x426b·D·p3b | `s9_soil_slope.ready_limit_s(case)`: 경사 120 s, 평지·패드 B·J1/J2/S1 100 s, 그 밖 평지 90 s | **기록(FLAG)**, P3-6 | `s9_soil_slope.py` 204~206·600~607·736행, `u3_u6_rerun_rules.md` 52행 |
| U-3 g6·C | 120 s | 판정 항목 아님(r72 승격 표시 `ready>120`) | `r72_judge.py` 42행 |
| U-3 g8 | 없음(확인한 범위에서 g8 판정에 시각 한계 없음) | — | `s9_slope_fix_candidates.py`(337행 +5 s는 수정 후보 채택 규칙) |
| U-6 C2·ABL·IND | 없음(lite 관문 = READY 도달 ∧ FAULT 없음) | — | `b5_baseline_compare.py` 1064행 |
| C-5 | `READY_le_120s`(G6 대응) + P3-6 | 판정 항목 | `README_judges_4368.md` 117행 |

- 따라서 E-1은 U-3에서는 FLAG로만 나타나고 U-6에서는 나타나지 않는다. 판정 미달로는 D-1과 C-5에서만 나타난다. 판정서는 등급 악화를 FLAG·안전 종료·미달로 나눠 적는다.

### 4.4 E 항목별 436.8 관문 ID

| E | D-1(H-1) | U-3(H-3) | U-6(H-4) | C-5 |
|---|---|---|---|---|
| E-1 | H-R READY 90/120 s, H-S P3-6 100/120 s(`d1_selection_rules.md` 166·167행) | P3-6(FLAG, 6개 연구) | 해당 없음 | `READY_le_120s`, P3-6 |
| E-2 | H-R 끝 자세 ≤ 0.2°·READY 항목, H-S P3-1~P3-9 가운데 READY에 기대는 항목(166·167행) | P3 행(`s9_soil_slope.p3_rows`)의 READY·끝 자세 항목, G6-6(READY 도달 ∧ FAULT 없음, g6·C), g8 판정의 READY 도달 | lite `ready_no_fault`, 공식 `fault_ready` | G6-6, `READY_le_120s`, P3-1·P3-4·P3-5 |
| E-3 | H-R FAULT 0(166행), H-S `stroke_limited_stop` 허용(167행) → 안전 종료 | 427.12 `stroke_limited_stop` 허용 → 안전 종료 | 429.11 IND 안전 종료 따로 셈 | 427.9 `allowed_stop`(통과 쪽, 결정 65·107) |
| E-4 | 해당 없음 | 해당 없음 | 해당 없음 | 해당 없음 |
| E-5 | I4 기대 분류 관문 없음 → 해당 없음 예상(기록 R-8) | 같음 | 같음 | 같음 |
| E-6 | H-R FAULT 0 | P3 FAULT 항목, G6 FAULT 항목 | `fault_ready` | G6-6 |

- P3-1~P3-9의 항목별 뜻은 `s9_soil_slope.p3_rows`의 정의다. 분류 스크립트는 항목 이름을 이 표의 칸에 그대로 대응시킨다.
- 대응에 쓰는 항목 이름 목록은 TA 경로 1 `imua` 모드 출력의 항목 이름(3.3.2절)으로 봉인 때 스크립트 상수로 고정한다. 지금 `classify`는 `gate_in_family`를 입력으로 받는다(구현 보고 5절).

## 5. 현행 IMU 짝 비교 기록 (판정 아님)

- **집락(셈 단위) = `cluster`, 재표집·유효 표본 수 단위 = `resample_unit`.**
  - 대응표: D-1 = `job.d1.key`(ε 짝은 한 단위), U-3 = 봉인 때 고정한 `u3_cluster_map_r1.csv`(cluster 376, resample_unit 284), U-6 = `case`(242), Chrono = 행
  - 대응표는 결과 전에 sha로 고정한다.
- 정체성 관문(3절)을 통과한 경우에만 "A형 효과"로 쓴다.
- 436.8 짝은 사용자 결정 2026-11-28대로 현행 IMU 짝 비교 자료로만 쓴다. 판정서 한계 절에 "436.8: 사전 등록 판정 불가, rev26 사후 재판정 종합 미달(참고)"을 적는다. 합격 주장은 A형 봉인 결과로만 한다.
- 유효 표본 수(설정당)
  - D-1 217(재표집 단위 = 키)
  - U-3 **약 50**: 재표집 단위 284, Kish 단위 46.6, 줄 가중 평균 크기 23.9, 436.8 READY ICC 0.930(V0)·0.923(VB) 실측, 설계 효과 22, 유효 표본 수 50.0·50.3. 셈 단위 376 기준으로는 약 206(stats 검토 3 `u3_r1_neff.json`)
  - U-6 C2 242
  - Chrono는 행 단위

| # | 기록 항목 | 정의 |
|---|---|---|
| R-1 | 첫 READY 시각 차 | 묶음 × 설정 층(U-3은 연구 층도)마다 재표집 단위 안 줄 평균을 먼저 낸다. 이어서 다음 규칙을 따른다. ① **구간은 재표집 단위 평균의 단위 가중 중앙값·90 백분위에만 붙인다.** 줄 가중 값은 점추정만 적는다. ② 구간은 층 안에서만 재표집 단위를 재표집한 백분위 95 %(B = 10,000, 시드 20261114)다. ③ 구간을 내는 층은 재표집 단위 ≥ 50인 층이다: D-1 설정당 217, U-3 묶음 층 284·slope 110·g6+C 75·p3b 51, U-6 242. g8 12·x426b 24·h6 8·h9 4·D 3과 Chrono는 최소·중앙·최대만 적는다. ④ A가 READY 없음이면 지연을 +∞(오른쪽 중도 절단)로 두고 순위 통계에 넣는다. 두 팔 모두 READY 없음이면 뺀다. 절단 비율이 10 %를 넘는 층은 90 백분위를 "정의 안 됨"으로 적는다. ⑤ **모의 포괄률은 명목 95 %에 대해 0.91~0.95다**(묶음 층 284 단위: 중앙값 0.930, P90 0.941. 51 단위 층: 0.928·0.915). ⑥ **U-3 묶음 층의 단위 가중 값은 g8(줄의 46 %)을 284 단위 가운데 12(4 %)로만 센다. 그래서 줄 가중 점추정과 연구 층 값을 같이 읽는다** |
| R-2 | READY 뒤 재레벨 | `n_ready_relevels`, 꼬리 뒤 명령 최대(개정 2 G5b 정의), READY를 잃고 끝난 줄 수 |
| R-3 | 탐침 회수·PROBE 안 재레벨 | DONE → PROBE 횟수, PROBE → LEVEL 횟수 |
| R-4 | LEVEL 시간·첫 DONE 시각 | 차의 분포 |
| R-5 | 끝 자세 | READY로 끝난 줄의 max(\|roll\|, \|pitch\|) 차 |
| R-6 | 이탈 뒤 최소 다리 힘 | 차, $F_{min}$ + 5 kN 미만 행 |
| R-7 | 정지 종류 | SGS, S-4, 427.9 `allowed_stop`, 새 FAULT 수 |
| R-8 | READY 중 GE1′ 관문 열림 비율, `WARN_SUPPORT_CHANGED` 수 | 두 팔 |
| R-9 | 압력 진단 사건 | D1′·D1″ 계열 WARN·FAULT 수 |
| R-10 | 등급 전이 | 통과 → 미달, 미달 → 통과 줄 수와 함께, 전이가 하나라도 있는 집락(`cluster`) 수를 방향별로 적는다. 두 방향이 섞인 집락은 "혼합"으로 센다. FLAG·안전 종료 전이는 따로 센다. 짝 검정(McNemar 등)은 하지 않는다. 비율을 쓰면 집락 단위 k/n과 Clopper–Pearson 95 % 구간을 쓴다 |
| R-11 | 4.2 분류 | E-1~E-7 "설명됨" 수, 사유별 "설명 안 됨" 수, 짝 판정 불가 수, 특이도 지표, 양성·음성 대조 결과, 2.2절 기록 실패 수 |
| R-12 | U-9 인용 | `imua_check` A-v5 G1~G5b·G4d. A형 근거는 fail(G1·G4·G5b) |
| R-13 | 논문 4절 주장별 A형 근거 | 봉인 때 sha로 고정하는 `v5paper_imua_claims.md`(주장 → 묶음 대응, A형 근거 있음 / 확인 실행만 / 없음, 근거 낱말, 제외 사유). 결과 뒤 묶음을 더하거나 빼지 않는다. 더하면 "결과 뒤 추가"로 표시한다. 논문 요약 문장은 "A형 결과가 있는 묶음 기준"으로 범위를 적는다. H-6~H-12는 "축소안 밖"으로 적는다 |

- **C-5**는 행 단위 기록(행마다 436.8 → A 전이와 기전)만 낸다. 비율 진술은 하지 않는다.
  - 불가피하면 k/n과 CP 95 % 구간을 함께 적는다(0/24 → 상한 14.2 %, 0/11 → 28.5 %, 0/6 → 45.9 %, 1/6 → 0.4~64 %).
  - VB↔V0 여섯 쌍은 쌍마다 기술한다.
- U-3 slope의 D-1 재사용 12줄(436.8 원판 115행)은 D-1과 같은 실행이다. 묶음을 합친 요약을 내면 한 번만 센다.
- U-6 C2↔IND 비교에는 1.2절의 IND A형 여유 저하(가정 모델 PM −6.0°, $M_s$ +0.28)를 함께 적는다.

## 6. 멈춤 조건

- 3절 전제 미충족, 정체성 관문 불일치, 판정 행 수 불일치([정의 A-3])는 설정 결함이다. 멈추고 보고한다.
- TA0 병합에서 `.gitattributes` 밖의 충돌이 나면 TA를 만들지 않는다. 멈추고 확인 필요로 올린다.
- 3.1절 대체 조건 1~3·6 불충족, J-2 불일치는 설정 결함이다. A형 묶음을 시작하지 않는다.
- J-2c 불일치는 C-5만 설정 결함이다. C-5 A형 실행·판정을 하지 않는다. 하네스 묶음은 진행할 수 있다.
- `imua_expected_imu_sensor.json`을 RA에서 다시 만든 결과가 봉인본과 다르면 실행하지 않는다(설정 결함).
- P-7 양성·음성 대조 불일치가 나면 봉인하지 않는다.
- H_I를 바꾸면(실행 코드 변경) 3.1절 TA 조립과 J-2·J-2c를 다시 하고 앞 결과를 공개한다. 같은 RA로 본 실행을 두 번 하지 않는다.
- 실행 오류 줄, `MIXED_HULL_MODE`, 스레드 수 기록 불일치(SCM)는 436.8 원판의 멈춤 규칙대로 처리한다(실행 오류).
- 판정 도구의 멈춤 표지는 436.8 원판 13절 2항대로 사용자가 결정한다. C-5 경로 2 CD-7 빈 사유는 4.1절대로 처리한다.

## 7. stats-design-expert 검토 반영 기록

- 검토 1~3(SHA256SUMS 포함). 세 검토의 rev26 부분은 [오염 후]다(436.8 H-3·H-4 원 판정 세부를 읽은 뒤 작성). rev26 권고는 rev26 문안에만 쓰고 이 문서의 A형 판정 정의에는 쓰지 않는다.
- 검토 1 반영: 1(집락·R-10), 2(조건 4·5, E-5·E-2 서명, 분류 스크립트, 특이도, 짝 판정 불가, 기대 건수), 3(R-1), 4(정체성 표본·diff·검출력·I-C SCM), 5(R-13), 6(C-5), 그 밖(H-4 행 수, 기대 태그, 상태 순서, 6절 rev26, H-1 낱말 없음)
- 검토 2 반영: B-3(재표집 단위·유효 표본 수), R-6(재접근 배제), R-7(양성 대조), R-10(구간 규칙), R-11(D-1 재사용 줄), R-12(아래)
- 검토 3 반영: S-3(유효 표본 수 실측), S-5(포괄률 0.91~0.95), S-6(g8 가중 공개), S-7(E-1 재표집 문장 정정), S-8(음성 대조 합성 1건). S-4(`u3_neff.py`)는 P-7이다.
- **R-12**: stats는 검토 1 7번의 "후보-7을 S-3으로" 권고를 검토 2에서 철회했다(4.2 기록 확인을 넓게 읽은 오류). S-2 정렬을 받아들였다.
- stats는 검토 3에서 재표집 단위 284와 표지 꼴 `IND_LAS:<사유>`를 타당하다고 판단했다.
- 검토 4(수정 11 뒤, 대기): 8절 Q-S1

## 8. 확인 필요

- Q-U6: **결정(사용자, 2026-11-22): (가).** IND·IND_LAS도 같은 경사계로 다시 돌린다. 센서 조건만 같게 하고 C8 제어 상수는 바꾸지 않는다. 경사계 입력 해석은 1.2절이다(control-expert 판단: 저역통과 유지).
- Q-H2: H-2 선별로 정해지는 D-1 Chrono 행을 뺀 것의 논문 서술은 논문 작성 단계에서 정한다(R-13 주장 목록에 "제외 사유: 비용").
- **Q-U1(사용자)**: G-d Chrono A형 가동 확인 1행(C-5 35행 밖 짧은 L2b 1행, 값은 판정·예측에 쓰지 않고 공개)을 할지
  - 추천: **한다.** C-5 A형 행에는 확인 실행이 한 번도 없다. P-8 재생기의 실제 기록 수용 시험도 이 행으로 할 수 있어, C-5 본 실행(55~150 스레드·h) 전에 C-1·P-8 결함을 잡는다.
- **Q-U2(사용자)**: J-2c(3.4절, 요청 밖 추가 1) 채택
  - 추천: **(가) 채택.** 대안 (나)는 C-5를 판정에서 빼고 행 기록만 낸다. (나)를 고르면 C-5 A형 결과가 "판정"이 아니게 되어 R-13 주장 범위가 줄어든다.
  - 근거: C-5 판정 도구가 R3f 뒤 두 경로 모두에서 바뀌었고, J-2는 하네스만 덮는다.
- **Q-U3(사용자)**: H-12(T4h 재생 기록)를 A형에서 "해당 없음(축소안 밖)"으로 둘지(요청 밖 추가 2)
  - 추천: **그렇게 둔다.** 경로 1만의 기록 묶음이고 등급이 없다. A형 자세 기록은 2.2절의 별도 폴더가 맡는다.
- **Q-U4(사용자)**: C-5 경로 2 CD-7 빈 사유 멈춤에 436.8 결정 107 (2) 처리를 결과 전에 그대로 적용할지(요청 밖 추가 3)
  - 추천: **적용.** 적용하지 않으면 A형 C-5 경로 2가 436.8과 같은 이유로 멈춰 판정 불가가 될 가능성이 크다.
- **Q-U5(사용자)**: `imu_sensor` 비교 범위(1.1절)
  - 추천: **(가) 블록 전체.** 대안 (나)는 키 일부(`model`·`gains_preset`·게인 세 값)만 본다. (나)는 센서 파라미터가 달라진 것을 놓친다.
- **Q-U6(사용자)**: E-2 계산 정의 수정 2건(4.2.1절 (iv) 판독 수 21, (vi) 기록 끝 창 = 평가 불가) 채택(요청 밖 추가 4)
  - 추천: **채택.** 구현 코드를 조금 고쳐야 한다(P-7).
- **Q-S1(stats-design-expert, 위임)**: 아래 넷을 stats가 정한다. 이 문서는 숫자를 정하지 않는다.
  - `u3_neff.py` 수정 위치(SUMS가 있는 stats 근거 폴더 `v5paper_imua_stats/`의 파일을 고칠지, 새 파일 `u3_neff_r2.py`로 둘지)와 수정 내용(S-4)
  - E-1 U-3·E-2 D-1 기대 건수·97.5 % 상한 스크립트의 소유와 위치
  - 4.2.1 E-2 정의 수정이 기대 건수 계산에 주는 영향
  - 구현 보고 6절 6

## 9. stats 권고 가운데 바꿔 반영한 것 (이유)

| 권고 | 반영 | 이유 |
|---|---|---|
| E-2 서명 "재레벨 직전 완료 필터 자세 편차 > 0.07°" | 기록된 제어 필터 `attitude_filtered_deg` ≥ 0.065°(stats 검토 2 수용) | 완료 필터 값은 T4h에 기록되지 않는다. 제어 필터가 더 빨라 먼저 문턱을 넘는다(A2 관측 최소 0.0744°). 완료 필터 오프라인 재적용 값은 기록만 한다 |
| U-3 집락 휴리스틱(340) | 셈 단위 `cluster` 376 | g8의 다리·올림/내림 방향은 서로 다른 물리 사례로 둔다. 크기 변형만 묶는다 |
| U-3 재표집 단위 296(stats 검토 2) | `resample_unit` 284(stats 검토 3 수용) | g8 `ref|none|0` 대조 행은 같은 기본 경사의 짝이라 같은 단위다 |
| 후보-7을 S-3으로(rev26) | S-2로 맞춤(stats 검토 2 수용·철회) | 원판 80·281행 |

## 10. 봉인 전 채울 칸

- (채움) 4.4 E 항목별 436.8 관문 ID
- (채움) U-3 재표집 단위 284 기준 READY ICC와 유효 표본 수(5절)
- (채움, 수정 11) 2.1절 출력 이름 표, 2.2절 기록 위치·키, 3.3절 TA 작성 명세, 4.2.1절 E-2 계산 정의
- H_I 확정(C-1·P-7 나머지 반영 뒤)과 그 전체 해시
- 8절 Q-U1~Q-U6 사용자 결정, Q-S1 stats 검토 4
- E-1 U-3 기대 건수·상한, E-2 D-1 기대 건수·상한(P-7 실행값)
- 정체성 표본 목록(I-H 50 sha, RA에서 다시 생성)과 I-C 2행 ID
- P-7 양성·음성 대조 결과(4.2.1 수정 반영 뒤, RA에서) sha
- 봉인과 함께 고정할 파일의 sha: `u3_cluster_map_r1.csv`, `v5paper_imua_claims.md`, P-7 스크립트(분류·기대 건수·선정·기대 블록 생성), 수정된 `u3_neff.py`
- `imua_expected_imu_sensor.json`(RA 생성)과 sha. `chrono_c2`는 C-1 뒤
- 4.4 관문 ID 상수(TA 경로 1 항목 이름 표 뒤)
- TA 조립 기록: TA0·P1A·P2A·TA 해시, `ta_allowed_changes.tsv`, `allowed_src_changes.txt`, `ta_closure.json`과 닫힘 도구 이름·sha
- J-2 실행본 두 개(2회차 실행본 대비 diff)·sha, J-2 비교 결과
- J-2c: R3f 두 경로 Chrono 실행본 경로·sha, J-2c 실행본 두 개와 diff·sha, `j2c_excluded_fields.json`, J-2c 비교 결과
- A형 판정 실행본 네 개(하네스·Chrono × 두 경로)와 부르는 하위 명령 목록·sha
- TA 전용 worktree 경로·lock, `ta_identity.json`

### 부록 R11. 수정 11 근거 (2026-11-28, control-expert)

| 근거 | 명령·위치 | 결과 |
|---|---|---|
| 커밋 관계·파일 집합 | scratchpad `control-imua-r11/git_sets.py` → `git_sets.json` | 3.1절 "사실"의 수치 |
| R3f 이후 Chrono 판정 파일 | `control-imua-r11/git_chrono.py` → `git_chrono.json` | 3.4절 이유 |
| W 자료와 겹침 | `control-imua-r11/w_overlap.py` → `w_overlap.json` | 3.1절 `data_doc_w` 2개 |
| IND 소신호 여유 | `control-imua-r11/ind_loop.py` → `ind_loop.json`(dynamics-dev, python-control 0.10.2) | 1.2절 표 |
| 구현 확인(코드 읽기) | v5-imua worktree `b5_baseline_compare.py` 380~433행, `attitude.py` 95~139행, `c2.py` 5540~5579행, `imua_records.py` 전체, `imua_classify.py` 1~300행, `imu_a_harness.py` 40~239행, `u3_reuse.py` 255~284행, `run_v5.py`·`v5_rerun.py`(Grep) | 1.1·1.2·2.2·4.2.1절 |
