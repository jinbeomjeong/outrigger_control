# IMU 자세 전용 출력(경사계·AHRS) 비교 연구 설계 (2026-11-22, control-expert)

- 성격: **탐색 비교**다. 사전 등록 판정은 아니지만, 지표 정의와 비교 규칙은 결과를 보기 전에 이 문서로 고정한다(5절).
- 질문(사용자, 2026-11-22 승인): IMU가 가속도계 3축·자이로 3축 대신 roll·pitch만 출력하면 제어 성능이 얼마나 달라지는가.
- 작성 조건
  - 이 문서는 코드를 고치지 않았다. 선형 해석은 scratchpad에서 실행했고, 근거 파일은 `lin_evidence/`(SHA256SUMS)로 옮겼다(9절).
  - 판 4a·판 5 판정 값(`06_analysis/02_control/j_p3_cause/j9_runs/**`)은 열지 않았다.
- 규약
  - 음되먹임. 분리 채널은 $v=-Ky$, 다리 속도는 $u=[A,n]v$이고, 루프는 분리 명령 $v$에서 끊는다.
  - 이산 ZOH, $T$ = 0.1 s, d = 1이다. IMU 계산 주기는 $h$ = 10 ms(100 Hz)다.
  - 밸브는 1차 지연 $\tau_v$ = 0.1 s이고, 감도는 0.15 s로 본다.
  - 주파수는 rad/s로 쓰고 Hz를 병기한다. 각도는 deg로 쓴다.

## 0. 결론 미리보기 (선형 해석, 시간 응답 전)

| 항목 | A 경사계 | B AHRS(자세만) | C AHRS(자세 + 각속도) |
|---|---|---|---|
| 자세 루프(현행 이득) | **미달**: $M_s$ 1.63~1.81(내부 필터 0.3~1 Hz) | 현행과 같음: 1.402 | B와 같음 |
| 필요한 조치 | 자세 이득 Kp 0.2 → 0.12, Ki 0.01 → 0.006, 가드 $K_g$ 0.15 → 0.10. 제어기 필터 τ 0.8 × 2는 **그대로** 둔다(줄이면 악화) | 없음. 선택: τ_f 0.8 → 0.4 × 2(여유 개선) | B와 같음 |
| 탐침 자세 단서 | 쓸 수 없다(로킹 겉보기 기울기·지연). **끈다** | 센서 자세 차분으로 대체. 분해능 ≤ 0.001°가 필요하다 | 현행 그대로(자이로 적분) |
| B1′·GE1′ | B1′ 없음. GE1′은 자세 차분 | 같음 | 현행 그대로 |
| D1″($f_z$) | 못 쓴다 → D1′ | 같음 | 같음 |
| 1 s roll 각속도 | 자세 1 s 최소제곱 기울기 | 같음 | 현행 그대로 |

## 1. 현재 IMU 사용처 (코드 확인, 메인 목록 정정 포함)

| 기능 | 입력 | 위치 | 메인 목록 대비 |
|---|---|---|---|
| 자세 필터 2단 τ 0.8 s(100 Hz) → 자세 PI, 완료 필터(1차 1 s), 데드밴드, 시작 조건, 탐침 자세 한계(D4) | 10 ms 가속도 표본 → `roll_pitch_from_specific_force` | `c2.py` 5432~5460 `_filtered_attitude`·`_update_attitude_filters`, 4592~4604. 탐침 한계 `ground_contact.py` 957 | 1364행은 `R8Settings.imu_sample_period_s` 필드 설명이고, 실제 사용처는 5432행이다 |
| 원시 10 ms 기울기(필터 전) | 같은 표본 | CHECK 자세(P-R8-9) `c2.py` 7025~7040, 7106~7132. 정착 기울기(P-S9-4) 8484. S-1 평탄 창 8549. FAULT_REGROUND 기울기 기록 6785(중단 규칙은 프리셋에서 꺼짐, 2815) | **빠져 있던 항목** |
| 자이로 적분 자세(탐침 단서) | 주기 평균 자이로 − B1′ 편향 | `c2.py` 5465~5473, 9611~9620. `ground_contact.py` 424~504(Q1·Q1b 창 품질) | 맞음 |
| B1′ CHECK 편향 | CHECK 자이로 | `c2.py` 7017~7038, 7134~7190, `standstill.py` 59~172 | 보통 등급은 $T_b$ = 10 s라 **CHECK가 10 s 이상 걸린다**(이상 등급은 2 s) |
| GE1′ 정지 관문 | 편향을 뺀 주기 평균 자이로 | `c2.py` 5761~5780, `standstill.py` 223~294 | 그림자 계산만이 아니다. R6-G GE2(READY 재레벨·탐침)와 기준 갱신(5782~5799)의 관문이다 |
| 1 s roll 각속도(DSb75) | **원시** 자이로 표본(편향 미제거) | `c2.py` 8795~8807, 8826~8839 | 2315~2331은 상수·설명이고, 실제 계산은 8826행이다 |
| D1″ 헤드 계단 | 마지막 10 ms 비력 $f_z$ − 레버 항(자이로 표본 두 개) | `c2.py` 3841, 5341~5343. `two_pressure.py` 2052~2066, 1973~1991 | 맞음 |
| 크롤러 재접촉 감시(322.2), $M_{eff}$ | $f_z$ 잔차 | `two_pressure.py` 1636~1638(프리셋에서 켬, `c2.py` 2806), 2068~2107 | **빠져 있던 항목** |

- 입력이 없을 때 기존 처리: $f_z$가 없으면 D1″는 `WARN_D1_IMU_INPUT_MISSING`을 한 번 내고 D1′ 합 규칙으로 돈다(`two_pressure.py` 1984~1986). 이 연구에서는 경고 없이 명시 설정으로 바꾼다(6.2절).
- 하네스 차이
  - `c2py_r8d1_closed_loop.py` 136~143은 자이로 표본 없이 주기 끝 각속도 0을 준다.
  - `r79_sensor_screen.py` `SensorAdapter`(313~365)는 10 ms 자이로 표본을 준다.
  - 그래서 이 연구는 r79 경로를 쓴다.
- 참고: 지금의 등급 영점 오차는 두 경사계 제품에서 왔다(`attitude_sensor_survey.md`).
  - 우수 = ifm JN2101: 정적 경사계로, 사실상 A형이다.
  - 보통 = SICK TMM88D-MJI: 동적 경사계(자이로 융합)로, B·C형이다.
  - 그런데 시뮬레이션은 이 등급을 6축 원시 IMU로 써 왔다. 이 연구는 그 차이도 직접 보는 의미가 있다.

## 2. 대안 센서 모델

모든 모델은 기존 `ImuModel`(같은 등급, 같은 시드 스트림, 표본당 정규 난수 6개)이 내는 원시 가속도·자이로 표본 위에 **온보드 처리**를 얹는다.
- 그래서 잡음 난수열이 기준과 같다(공통 난수).
- 다리 센서 스트림(`SensorSuite`의 spawn 둘째)도 바뀌지 않는다.

### 2.1 식

| 기호 | 뜻 | 단위 |
|---|---|---|
| $\tilde\phi_a,\tilde\theta_a$ | 잡음·바이어스가 있는 10 ms 가속도 기울기 | rad |
| $\tilde\omega_x,\tilde\omega_y$ | 잡음·바이어스가 있는 자이로 | rad/s |
| $\tau_s=1/(2\pi f_s)$ | 경사계 내부 단 시정수 | s |
| $\omega_c=2\pi f_c$ | AHRS 가속도 보정 교차 각주파수 | rad/s |
| $k_P=2\omega_c,\ k_I=\omega_c^2$ | 상보 PI 이득(ζ = 1) | 1/s, 1/s² |
| $q$ | 출력 분해능(LSB) | rad |
| $p$ | 출력 지연 | 표본(10 ms) |
| $h$ | 표본 주기 0.01 s | s |

- A(경사계): $y_1\leftarrow y_1+\frac{h}{\tau_s}(\tilde\phi_a-y_1)$, $y_2\leftarrow y_2+\frac{h}{\tau_s}(y_1-y_2)$. 출력은 $Q_q(y_2)$를 $p$ 표본 늦춘 값이다(축마다 같다).
- B(AHRS, 작은 각): $e=\tilde\phi_a-\hat\phi$, $\hat b\leftarrow\hat b-k_I e\,h$, $\hat\phi\leftarrow\hat\phi+(\tilde\omega_x-\hat b+k_P e)h$. 출력은 $Q_q(\hat\phi)$를 $p$ 표본 늦춘 값이다. pitch는 $\tilde\omega_y$로 같은 식을 쓴다.
- B의 정상상태: 상수 자이로 바이어스는 적분기가 지운다. 그래서 자세 영점 오차는 가속도 영점 오차와 같고, 등급 예산(0.14° / 0.118°)도 그대로다.
- C: B의 자세에 원시 자이로 각속도(현행 `ImuModel` 출력 그대로)를 더한 것이다.
- 출력 주기는 모두 10 ms(100 Hz)다. 비력·$f_z$는 어느 모델에도 없다.

### 2.2 대표값 (모두 **가정**, 제품 근거는 위임 1)

| 항목 | A 경사계 | B·C AHRS | 근거 |
|---|---|---|---|
| 내부 대역 | 2단 1차, $f_s$ = **1 Hz**(감도 0.5 Hz) | $f_c$ = **0.05 Hz**(ζ 1, 바이어스 적분 켬) | A: 조사 문서 "LPF 0.5~1 Hz(1차 1 Hz 군지연 0.16 s)". B: 선형 해석이 요구하는 $f_c$ ≤ 0.05 Hz(3절) |
| 출력 지연 | **20 ms**($p$ = 2) | **10 ms**($p$ = 1) | 처리 + CAN 전송(가정). 감도 +10 ms |
| 출력 주기 | 10 ms | 10 ms | 현행 IMU와 맞춤 |
| 분해능 | **0.01°** | **0.001°**(감도 0.01°) | 산업용 경사계 대표값(가정). B는 탐침 단서 요구(4.2절) |
| 영점·잡음·자이로 오차 | 등급의 가속도값(이상 / 우수 0.046° / 보통 0.072°, 15 / 82 µg/√Hz) | 등급의 가속도·자이로값(ARW 0.15 / 0.30 °/√h, 바이어스 5 / 20 °/h) | `imu.py` `IMU_GRADES` 그대로(공통 난수) |
| 시작 | 첫 표본 기울기로 필터 초기화 | **웜 스타트**: $\hat\phi_0$ = 첫 가속도 기울기, $\hat b_0$ = 등급 자이로 바이어스(엔진 시동 뒤 수렴했다고 가정). 감도: 콜드($\hat b_0$ = 0) | 실기는 레벨링 전에 전원이 켜져 있다고 가정 |

## 3. 선형 해석 (기존 정확 다율 모델)

- 모델: `04_scripts/03_control/r8d1/r8d1_lin.py`(명세 개정 30의 lifted 모델, 읽기 전용), 80개 플랜트 목록 `catalogue_ext`.
- 플랜트의 `phi_acc`·`theta_acc` 출력을 2.1절 연속 센서 상태로 바꾸어 플랜트에 덧붙였다. 지연은 `p_imu`로 넣었다.
- C2 프리셋 값: Kp 0.2 s⁻¹, Ki 0.01 s⁻², τ_f 0.8 s × 2(100 Hz), Ktw 0.5 s⁻¹ / $k_{nom}$, τ_tw 0.2 s, Kz 0.5, τ_z 0.2, 가드 $K_g$ 0.15 s⁻¹.
- 가드 활성 해석: 패드 지지 40개 플랜트 × 네 다리.
- 기준(명세 131절)
  - (1) 채널 $M_s$ ≤ 1.5
  - (2) 가드 활성 $M_s$ ≤ 1.5
  - (3) 다리 디스크 여유 α ≥ 0.6은 **계산하지 않았다**(2단계 항목).

| 변형 | 채널 최악 $M_s$(> 1.5 개수) | 가드 활성 | 자세 PM 최소(첫 교차) | 자세 GM 최소 | 지연 여유 최소 | $\omega_{gc}$ [rad/s] |
|---|---|---|---|---|---|---|
| S0 현행 | **1.391**(0) | 1.391 | 54.0° | 4.79(13.6 dB) | 4.68 s | 0.107~0.205 |
| S0 + 10 / 20 ms | 1.416 / 1.455 | — | 53.9° | 4.60 / 4.01 | 4.66 s | 같음 |
| S0, τ_v 0.15 | 1.407 | 1.407 | 53.7° | 5.17 | 4.63 s | 같음 |
| A 5 / 2 / 1 / 0.5 / 0.3 Hz | 1.824 / 2.312 / **1.707(19)** / 1.626(80) / 1.804(80) | — / — / 1.791 / 1.626 / — | 53.5 / 52.8 / 51.0 / 47.3 / 42.5° | 2.83 / 1.94 / 2.48 / 3.79 / 3.13 | 4.35 s(1 Hz) | 같음 |
| A 1 Hz, 지연 0 | 1.665(3) | — | 51.2° | 2.53 | — | — |
| A 1 Hz, τ_f 0.64 / 1.0 | 2.620 / 1.624 | — | — | 1.62 / 3.78 | — | — |
| A 1 Hz, 제어 필터 1단(n = 1) | 8.69 | 8.72 | — | 1.14 | — | — |
| A 1 Hz, Kp 0.15 / Ki 0.0075, $K_g$ 0.15 / 0.10 | 1.455 | 1.670 / 1.521 | 49.1° | 3.30 | 5.85 s | 0.085~0.158 |
| **A 1 Hz, Kp 0.12 / Ki 0.006, $K_g$ 0.10** | **1.335**(0) | **1.480** | 46.3° | 4.13(12.3 dB) | 7.12 s | **0.071~0.130** |
| A 0.5 Hz, Kp 0.12 / Ki 0.006, $K_g$ 0.10 | 1.371(0) | 1.399 | 45.0° | 6.32 | 6.81 s | 0.071~0.129 |
| A 1 / 0.5 Hz, Kp 0.12, τ_v 0.15 | 1.318 / 1.381 | 1.420 / 1.381 | 46.1 / 44.8° | — | — | — |
| A 1 Hz, Kp 0.10 / Ki 0.005, $K_g$ 0.10 | 1.359 | 1.457 | 43.7° | 4.95 | 8.20 s | 0.062~0.111 |
| **B 0.05 Hz, τ_f 0.8** | **1.402**(0) | **1.486** | 53.9° | 6.25(15.9 dB) | 4.66 s | 0.107~0.205 |
| B 0.05 Hz + 20 ms | 1.406 | — | 53.9° | 6.18 | — | — |
| B 0.05 Hz, τ_v 0.15 | 1.418 | 1.458 | 53.6° | 5.93 | — | — |
| B 0.05 Hz, τ_f 0.5 / **0.4** / 0.3 / 0.2 | 1.267 / **1.270** / 1.323 / 1.506(1) | — / **1.460** / — / — | 57.6 / 58.9 / 60.1 / 61.4° | 8.00 / 8.75 / 5.66 / 3.58 | 5.17 / 5.35 / 5.53 / 5.72 s | 0.108~0.209 |
| B 0.05 Hz, τ_f 0.4, +30 ms / τ_v 0.15 | 1.328 / 1.292 | 1.493 / 1.465 | 58.8 / 58.6° | — | — | — |
| B 0.02 Hz, τ_f 0.4 | 1.224 | — | 58.9° | 9.54 | 5.35 s | — |
| B 0.1 Hz, τ_f 0.8 / 0.4 | 1.400 / 1.598(1) | **1.520** / — | 53.9° | 5.96 / 4.91 | — | — |
| B 0.2 Hz, τ_f 0.8 / 0.4 | 1.396 / 2.821(4) | — | — | 4.67 / 2.18 | — | — |

해석
- **A(경사계)**
  - 내부 저역통과의 위상 지연이 두 곳에서 여유를 깎는다.
    - (i) 저감쇠 로킹 봉우리: φ 5.9~7.0 rad/s(0.94~1.11 Hz), 마스트 대리 sup_lower 플랜트.
    - (ii) 자세 루프 저주파 PM: 0.5 Hz 이하에서 PM 47°로 떨어지고, 80개 플랜트 모두 1.5를 넘는다.
  - 가속도 경로라 로킹 겉보기 증폭(27~360배)도 그대로 들어온다.
  - 제어기 필터를 줄이면 나빠진다(2.62). 1단으로 줄이면 크게 나빠진다(8.7).
  - 그래서 **이중 필터는 그대로 두고 이득을 낮춘다.** 권고값은 Kp 0.12, Ki 0.006, $K_g$ 0.10이다. 대가로 교차 주파수가 약 35 % 낮아져 레벨링이 느려진다.
- **B(AHRS)**
  - 로킹 때 겉보기 기울기가 아니라 실제 자세(+ 가속도 누설)를 본다. 그래서 현행 필터 그대로 현행과 같은 여유가 나온다.
  - 필터를 τ 0.4 × 2로 줄이면 $M_s$ 1.27, PM 58.9°로 **개선**된다.
  - 단 $f_c$ ≤ 0.05 Hz가 필요하다. 0.1 Hz면 가드 활성 1.52, 0.1 Hz와 τ_f 0.4를 함께 쓰면 1.60으로 미달한다. 이 값이 B 센서의 **요구 사양 후보**다.
- 모델 확인: 현행 S0와 S0 + 20 ms는 명세 132절 C2 값(1.391, +20 ms 1.455, PM 54.0°)을 재현했다.

### 3.1 로킹 잔류 (해석, 연속 근사)

- 진폭 가정(`imu_cabin_and_accuracy_review.md` 2.3): 상단 0.031°, 중단 0.021°, 하단 0.016°.
- 증폭 $G$는 2.2절 모드 표 값이다.
- B 출력은 $\phi(1+(G-1)H_{acc})$, $H_{acc}=(k_Ps+k_I)/(s^2+k_Ps+k_I)$다.

| 변형 | 제어 필터 출력 잔류 최악 [°] | 완료 필터 뒤 [°] | 최악 모드 |
|---|---|---|---|
| S0, τ_f 0.8 | 0.0179 | 0.00095 | 상단 2.98 Hz |
| S0, τ_f 0.4(참고) | 0.0707 | 0.0038 | 상단 2.98 Hz |
| A 1 Hz, τ_f 0.8 | 0.0024 | 0.0002 | 상단 1.78 Hz |
| B 0.05 Hz, τ_f 0.8 / 0.4 | 0.0007 / 0.0026 | 0.0001 / 0.0002 | 상단 1.78 Hz |
| B 0.1 Hz, τ_f 0.4 | 0.0048 | 0.0003 | 상단 2.98 Hz |

- B τ_f 0.4의 잔류는 현행 S0 τ_f 0.8보다 작다.
- 모든 변형이 완료 잔류 목표 0.005°(가정, 2.3절)를 만족한다.

## 4. 잃는 기능의 대체 규칙 (최소 변경)

### 4.1 자세 필터 입력
- A·B·C 모두 센서 자세 표본을 `AttitudeEstimator`에 바로 넣는다. 가속도→기울기 변환은 건너뛴다.
- 원시 기울기를 쓰던 곳(CHECK, P-S9-4, S-1, FAULT_REGROUND)도 같은 센서 자세 표본을 쓴다.
- 필터
  - A: τ 0.8 × 2를 유지하고 이득을 줄인다(3절).
  - B·C: τ 0.8 × 2(기본 팔)와 τ 0.4 × 2(선택 팔)를 둔다.

### 4.2 탐침 자세 단서 (`ground_contact` 결합 판정의 자세 반응)

| 대안 | 규칙 | 근거 |
|---|---|---|
| A | **끈다**(`ProbeSettings.attitude_cue = False`). 판정은 띠 ABOVE ∨ 강성. 자세 한계(D4, 필터 자세)는 그대로 둔다 | (1) 로킹 겉보기 기울기가 내부 1 Hz 필터를 거친 뒤에도 현행 자이로 적분 신호의 6.4배(1.78 Hz)·13배(2.98 Hz)다. 0.5 Hz에서도 2.0배·3.6배라 Q1(0.15 × 응답)에서 거의 늘 기권한다. (2) 내부 지연 때문에 유지 끝 창이 응답의 65 %(0.5 Hz)만 잡는다. 창 기울기 × 간격 비가 0.57(0.5 Hz) / 0.24(1 Hz)라 Q1b(0.25)에서도 기권한다 |
| B | 단서 = **센서 자세**(주기 표본 평균을 `rate_attitude_rad` 자리에 넣는다). 창 0.3 s·간격 0.76 s·Q1·Q1b·일치 비 0.5는 그대로 둔다. 바이어스 제거(B1′)는 하지 않는다(AHRS가 내부에서 추정) | 차분 잡음 1σ는 보통 0.0030° / 우수 0.0013°로, 현행 자이로 적분(0.0029° / 0.0014°)과 같은 수준이다. 위험 쪽 z(0.5 × 0.0236°)는 보통 3.9 / 우수 8.9(현행 4.1 / 8.2). 로킹 성분은 현행의 1.8배(1.78 Hz)·4.5배(2.98 Hz)라 Q1 기권이 늘 수 있다. 하네스에서 기권률을 잰다 |
| C | 현행 그대로(자이로 적분, B1′ 편향 제거) | — |

- **분해능 요구(B)**: 창 평균 차의 양자화 오차는 최대 1 LSB다.
  - LSB 0.01°: 위험 쪽 문턱 0.0118°의 85 %에 해당하고, 계단 하나가 Q1 비 0.42를 만들어 기권을 부른다.
  - LSB 0.001°: 8.5 %, Q1 비 0.04다.
  - 그래서 B의 요구는 **LSB ≤ 0.001°**(최소 0.002°)로 둔다. 감도 팔은 0.01°다.
- 잡음 계산 규약: 밀도는 단측 ASD다(`imu.py`의 σ = d√(1/2T)와 같은 규약). 명세 10.3 식($d\sqrt{\Delta t_c-\tau/3}$)은 같은 ARW에서 √2배 크게 나온다(명세 쪽이 보수 규약). 두 경로는 같은 규약끼리만 비교했다.

### 4.3 B1′·GE1′
- **B1′**
  - A·B는 각속도가 없다.
    - CHECK 끝에서 결과 `GyroBiasOutcome.NO_GYRO`(새 값)를 적고, CHECK를 늘리지 않는다. 사건 `INFO_GYRO_BIAS_NO_GYRO`를 한 번 낸다(경고 아님).
    - CHECK는 `check_time_s` 2 s, 영점 교정 왕복, P-R8-9 조용한 창으로 끝난다.
    - **주의**: 보통 등급 현행은 $T_b$ = 10 s라 CHECK가 10 s 이상 걸린다. A·B는 CHECK가 짧아지므로, 시간 지표는 TOUCH 시작 기준을 주 지표로 한다(5절 M2).
  - C는 현행 그대로다.
- **GE1′**
  - A·B: 관문 입력을 주기 자세 차분 $\hat\omega_k=(\bar\phi_k-\bar\phi_{k-1})/T$로 바꾼다. $\bar\phi_k$는 주기 k의 센서 표본 평균이고, roll·pitch 각각 따로 계산한다.
  - 잡음 보정에 쓸 σ는 같은 센서·등급으로 시드 0, 60 s 정지 모의를 돌려 $\hat\omega$ 표준편차를 재서 설정한다(`standstill_rate_noise_std_rad_s`).
  - 문턱(0.02°/s, 1 s 창, 0.5 s 유지, 명령 0 1 s)은 그대로 둔다.
  - C는 현행 그대로다.

### 4.4 D1″
- A·B·C 모두 $f_z$가 없다. 그래서 다음 세 가지를 **명시**한다. 그러면 경고 없이 D1′ 합 규칙으로 돈다.
  - `two_pressure.step_rule = "explained"`(D1′)
  - `crawler_recontact_watch = False`
  - `imu_mass_before_ready = None`
- 예상: 빠른 전방 침하 과도에서 거짓 헤드 고장이 생길 수 있다. 기록 재생 근거(명세 218.2/218.4): 100 bar 넘는 실제 헤드 계단 17개에서 D1′는 고장 3개, D1″는 0개였다.
- 크롤러 재접촉 의심(322.2)이 없어지므로 D1′가 그 상태까지 판정한다.
- 대체 후보(이번 범위 밖, 거짓 고장이 나오면 쓴다): 명세 218.4 (B) 지속성 규칙. 계단을 보면 의심으로 두고, 과도 뒤 0.5~1 s 정적 잔차로 확정한다.

### 4.5 1 s roll 각속도 (DSb75)
- A·B: $\phi'$ = 최근 1 s 센서 roll 표본의 **최소제곱 기울기**. 행정 기울기 $s'$와 같은 추정기, 같은 창을 쓴다.
  - 기울기 잡음은 σ√(12/N)/1 s 수준이라 무시할 수 있다.
  - A는 내부 지연 0.34 s만큼 늦다.
  - 로킹 성분은 최소제곱이 일부 걸러 낸다.
- C: 현행 그대로(원시 자이로 1 s 평균).

### 4.6 지표·한계로 남기는 것
- A의 탐침 자세 한계(D4): 필터 지연이 0.34 s 늘어 한계 초과가 약 0.014° 늘 수 있다(이동 속도 0.042°/s 가정). 탐침 중 실제 자세 변화 최대를 기록한다(M4).
- D1″ 레버 항은 $f_z$가 없으므로 해당 사항이 없다.

## 5. 지표와 비교 규칙 (결과 전에 고정)

- 진리값은 하네스 플랜트 상태다(센서 값이 아니다). 진리 기록에 데크 실제 roll·pitch를 추가한다(6.3절).
- 짝은 같은 (사례, 등급, 시드 색인)의 팔끼리다.
- 판정 행 0 = **판정 불가**다(통과가 아니다).

| # | 지표 | 정의 |
|---|---|---|
| M1 | 끝 자세 오차 | 첫 READY + 5 s 창(또는 실행 끝까지)에서 $\max(\lvert\phi-\phi_t\rvert,\lvert\theta-\theta_t\rvert)$, 실제 자세 기준. ±0.2° 판정은 장착 몫 0.02°를 더해 읽는다 |
| M2 | 첫 READY 시간 | 주 지표: $t_{READY}-t_{TOUCH\,start}$. 보조: $t_{READY}$(t = 0 기준), CHECK 길이, B1′ 결과 |
| M3 | 최소 다리 하중 | LEVEL 시작~첫 READY + 5 s 구간에서 1 ms 주기 최소 실제 힘(`force_min_N`)의 최소와 $F_{min}$ 배수(9.415 kN). $F_{min}$·$F_{min}$ + 5 kN 아래 표본 수 |
| M4 | 탐침 | 라운드 수·시간. 다리별 판정 대 진리(탐침 시작 실제 힘 > 1 kN = 접지, **가정**). 위험 쪽(뜬 → 접지)·안전 쪽 오판 수, 자세 단서 기권률(Q1·Q1b), `probe_unresolved`, 재접지 수, 탐침 중 실제 자세 변화 최대(D4 ±0.1°) |
| M5 | FAULT·안전 정지 | FAULT·FAULT_REGROUND·SGS 정지(`FAULT_LIFT_STROKE_LIMIT:soil`)·IDLE 거부·시간 초과(READY 없음) 횟수 |
| M6 | 거짓 압력 고장 | 주입 없는 실행의 헤드·로드 고장(`INFO_HEAD_PRESSURE_FAULT_REASON`, 대체 시작) 수, D1 설명 사유별 계단 수. A·B·C에서 `WARN_D1_IMU_INPUT_MISSING` = 0인지 확인(설정 오류 검사) |
| M7 | 데드밴드 진입 진동 | 첫 DONE 직전 10 s 자세 명령 성분 부호 반전 수(\|u_att\| > 0.02 v_max), 첫 DONE 뒤 DONE → LEVEL 복귀 수, 첫 READY 뒤 30 s 재레벨 수, 완료 필터 편차의 0.03° 교차 수 |
| M8 | 보조 | GE1′ 관문 열림 비율(READY), GE2 재레벨, DSb75 유지 시작 수·시간, LOC·LOC 취소 |

비교 규칙(**가정**, 탐색용 범주이며 채택 판정이 아니다)
- 팔별로 R0 대비 짝 차이의 중앙값·최대·개수를 낸다.
- 짝마다 아래 중 하나라도 해당하면 **악화**로 센다.
  - M1이 +0.02° 넘게 증가
  - M2가 +10 %와 +3 s를 모두 넘음
  - M3가 −2 kN 넘게 감소
  - M4 위험 쪽 오판 1건
  - M5·M6 새 사건 1건
- 반대 방향이면 **개선**, 나머지는 **동등**이다.
- 묶음 요약은 등급(L1·L2)과 사례군(g6core·g8·ref·lvl)으로 나눈다.

## 6. 구현 명세 (python-expert)

### 6.1 센서 (`03_src/outrigger_sim/sensors/attitude_only.py`, 새 파일)
- `AttitudeSensorKind(StrEnum)`: `inclinometer`, `ahrs`, `ahrs_rate`.
- `AttitudeSensorConfig`(frozen): `kind`, `sample_period_s=0.01`, `internal_filter_hz=1.0`, `internal_filter_stages=2`, `complementary_hz=0.05`, `bias_estimation=True`, `delay_samples`(A 2, B 1), `resolution_rad`(A 0.01°, B 0.001°), `start="warm"|"cold"`, `to_meta()`.
- `AttitudeSensorModel(imu_config, att_config, seed)`
  - 안에 `ImuModel(imu_config, seed)`를 둔다(같은 난수 소비).
  - `measure(t, specific_force, rate) -> AttitudeReading(t, roll_rad, pitch_rad, rate_rad_s | None)`. 2.1절 식이다.
  - 필터는 `CascadedLowPass(τ_s, 2, h)`(전진 오일러, $a=h/\tau_s$)를 쓴다.
  - `reset()`이 있어야 한다.
  - `rate_noise_std_rad_s(period_s)`: 시드 0, 60 s 정지로 GE1′ σ를 낸다.
- `Measurements`(signals.py)에 선택 필드 `imu_attitude_samples_rad: (n, 2) | None = None`을 더한다. 자세 센서일 때 다른 필드는 이렇게 채운다.
  - `specific_force_m_s2` = 마지막 자세의 단위 중력 벡터 $g(-\sin\theta,\sin\phi\cos\theta,\cos\phi\cos\theta)$. 합성값이고 측정값이 아니라고 문서에 적는다.
  - `angular_rate_rad_s` = C면 각속도 평균, 아니면 0.
  - `imu_specific_force_samples_m_s2 = None`.
  - `imu_angular_rate_samples_rad_s` = C면 표본, 아니면 None.
- `SensorSuite(..., attitude_sensor: AttitudeSensorConfig | None = None)`
  - None이면 지금과 비트 동일하다.
  - 값이 있으면 IMU 스트림(spawn 첫째)으로 `AttitudeSensorModel`을 만든다.
  - `setup()` 메타에 `attitude_sensor`를 더한다(None이면 키 없음).

### 6.2 제어기 (`control/c2.py`, `ground_contact.py`, `standstill.py`)
- 새 설정
  - `ImuOutputs(StrEnum)`: `full`(기본), `attitude`, `attitude_rate`. `C2Config.imu_outputs = ImuOutputs.FULL`.
  - `AttitudeOnlySettings`(frozen, `C2Config.attitude_only`)
    - `probe_cue: Literal["auto","rate_integral","sensor_attitude","off"]="auto"`. auto는 full·attitude_rate이면 rate_integral, attitude이면 sensor_attitude다.
    - `standstill_rate_noise_std_rad_s: float = 0.0`
    - `diff_sink_roll_rate: Literal["auto","gyro_mean","attitude_lsq_slope"]="auto"`
- 동작(`imu_outputs != full`일 때만)
  - `_filtered_attitude`: `imu_attitude_samples_rad`가 필수다(없으면 ValueError). `AttitudeEstimator.update_angles(t, roll, pitch)`(새 메서드)로 넣고, 원시 기울기 = 센서 표본으로 둔다.
  - `_update_attitude_filters`
    - `attitude`: `rate_attitude_rad` = 주기 센서 표본 평균(probe_cue = sensor_attitude). `gyro_rate_rad_s`는 GE1′용 4.3절 차분이다.
    - `attitude_rate`: 현행 그대로다.
  - B1′: `attitude`에서는 `GyroBiasOutcome.NO_GYRO`, CHECK를 늘리지 않고, `INFO_GYRO_BIAS_NO_GYRO`를 한 번 낸다.
  - `StandstillGate`의 σ = `standstill_rate_noise_std_rad_s`(attitude일 때).
  - DSb75: `attitude_lsq_slope`면 `sink.gyro_roll` 대신 최근 1 s 센서 roll 표본(시각, 값)의 최소제곱 기울기를 쓴다.
  - `ProbeSettings.attitude_cue: bool = True`.
    - False면 `evaluate_probe`에서 ratio NaN, `shows_attitude_response` False, `is_consistent` None이다. 띠·강성 판정은 그대로다.
    - probe_cue = off일 때 controller가 False로 넘긴다.
  - 검증
    - `imu_outputs != full`인데 `two_pressure.step_rule == explained_imu`이거나 `crawler_recontact_watch`가 켜져 있으면 **ValueError**다(조용한 대체 금지).
    - `r8.imu_sample_period_s`가 필수다.
- 프리셋 보조 함수: `C2Config.with_imu_outputs(outputs, *, probe_cue="auto", attitude_time_constant_s=None, attitude_kp=None, attitude_ki=None, guard_kg=None, rate_noise_std=0.0)`
  - `replace`로 위 값과 D1′ 설정(4.4절)을 함께 건다.
  - 이득 키는 `gains.attitude_kp_1_s`·`attitude_ki_1_s2`·`guard_kg_1_s`다.
- 메타에는 `imu_outputs`와 `attitude_only`(해석된 auto 값 포함)를 남긴다.
- **기본값(full)은 `C2Config()`·`with_10hz_d1()` 모두 기존 명령·사건·메타와 비트 동일**해야 한다. 새 메타 키는 full일 때 넣지 않는다.

### 6.3 하네스 구동기 (`04_scripts/03_control/s8/imu_attitude_study.py`, 새 파일)
- `r79_sensor_screen.py`는 import만 하고 **파일을 바꾸지 않는다**. 그 sha를 run.json에 기록한다.
- 작업자 안에서 `SensorAdapter`를 자세 센서판으로 바꾸고, 제어기를 팔 설정으로 다시 만든다. 순서는 `_rebuild_controller`와 같고, `level_config` 뒤에 `with_imu_outputs`를 적용한다.
- 진리 기록에 데크 실제 roll·pitch(플랜트 상태)를 추가한다.
- 팔(arm)

| 팔 | 센서 | 제어기 |
|---|---|---|
| R0 | 현행 IMU | v5 프리셋 그대로 |
| R0-d1p | 현행 IMU | + D1′(step_rule explained, 재접촉 감시 끔). $f_z$ 손실만 분리해서 본다 |
| A-k | A 1 Hz, 20 ms, 0.01° | attitude, probe_cue off, 이득 그대로 |
| A-g | 같음 | A-k + Kp 0.12, Ki 0.006, K_g 0.10 |
| B-k | B 0.05 Hz, 10 ms, 0.001°, 웜 | attitude, sensor_attitude, τ_f 0.8 |
| B-r | 같음 | B-k + τ_f 0.4 |
| C-k | C(B 자세 + 자이로) | attitude_rate, τ_f 0.8 |
| 감도(H3) | A-g05(f_s 0.5 Hz), B-r-q10(LSB 0.01°), B-r-cold, C-r(τ_f 0.4) | — |

- 등급
  - L1: 압력·IMU 이상(센서 구조 = 필터·지연·분해능은 있음)
  - L2: 압력 normal + 영점 교정, IMU normal_zeroed
  - 시드 색인 0~2. 시드식은 r79 H-4 그대로이며 팔과 무관하다(그래서 짝이 된다).
- 사례 집합 `imuatt` = g6core 48 + g8 50 + ref 21 + lvl 10 = **129**.
  - lvl = 강체, 패드 B, 오거 중단·하단 × 바닥 (0,0)·(roll +3°)·(pitch +2.5°)·(pitch −2.5°)·(roll +2°, pitch +2°).
  - ref 경로에 오거 단계를 주입할 수 없으면 구현을 멈추고 보고한다.
- 인자: `list | run --arms R0,... --levels L1,L2 --seeds 0,1,2 --set imuatt --workers 12 --affinity 0x0FFF0000 --pool E --out-dir <folder> --resume [--filter ...]`
  - 작업자마다 E코어 하나씩 고정한다(EcoQoS 해제는 하지 않는다).
- 출력
  - `<out>/imuatt_<arm>_<level>.jsonl`: 키·팔·등급·시드·센서 메타·제어기 메타·사건·진리 요약·`commands_sha256`·wall_s·peak_wset
  - `imuatt_run.run.json`: 커밋·is_clean·c2.py·r79 sha·시작/끝
  - `imuatt_run.sha256`
- 제어기 태그는 `<base_tag>_IMUATT-<arm>`이다. 재생 도구가 이 태그를 거부하게 한다(ideal 연구와 같은 방식).
- 종료 코드: 0 완료, 1 실행 오류, 2 입력 오류.

### 6.4 지표 스크립트 (`04_scripts/03_control/s8/imu_attitude_metrics.py`)
- 5절 M1~M8을 실행별로 계산한다(`imuatt_metrics_runs.json`).
- 짝 표 CSV(`imuatt_pairs.csv`): 사례·등급·시드 × 팔, R0 대비 차이와 범주.
- 요약 JSON: 팔 × 등급 × 사례군.
- 그림(PNG, 축 단위 표시): M1 [deg], M2 [s], M3 [kN] 팔별 분포, M4 기권률·오판 막대.
- 판정 행이 0이면 그 칸에 "판정 불가"를 쓴다.
- 모든 팔이 같은 키 집합인지 확인하고, 누락 키는 따로 적는다.

### 6.5 시험 (`05_tests/unit/test_attitude_only_sensor.py`, `test_c2_imu_outputs.py`, `test_imu_attitude_study.py`)
1. 기본값 비트 동일: 기존 c2 회귀 시험이 전부 통과하고, `SensorSuite(attitude_sensor=None)` 출력이 지금과 같다.
2. 공통 난수: 자세 센서를 켜도 다리 판독(헤드·로드·행정) 배열이 끈 경우와 비트 동일하다.
3. 경사계: 정지 기울기 + 영점 오차로 수렴(≤ 1e-9 rad). 계단 응답이 2단 이산 필터 식과 같다. 지연 2표본. 양자화 LSB.
4. AHRS
   - 정지 기울기 + 자이로 바이어스에서 수렴 오차 ≤ 1e-6 rad(바이어스 적분).
   - 겉보기 기울기 1.78 Hz × G 27 합성 입력의 출력 진폭이 해석값 $\lvert1+(G-1)H_{acc}\rvert$와 2 % 안에서 맞는다.
   - 웜/콜드 시작 차이.
5. 제어기
   - attitude + explained_imu → ValueError.
   - 합성 자세 표본에서 필터 자세가 `AttitudeEstimator.update_angles` 직접 계산과 같다.
   - B1′ NO_GYRO에서 CHECK가 `check_time_s`(영점 교정 끝)에 끝난다.
   - 센서 자세 단서: 0.0236° 계단에서 비 1.0 ± 0.02. probe_cue off면 비 NaN, 판정 = 띠 ∨ 강성.
   - DSb75 최소제곱 기울기 = 램프 속도.
   - GE1′ 자세 차분 관문: 일정 자세에서 열리고 0.05°/s 램프에서 닫힌다.
6. 구동기
   - 같은 커밋에서 R0 팔(L1·L2 s0, r79 identity 20키)의 `commands_sha256`이 `r79_sensor_screen.py` 직접 실행 값과 같다.
   - A·B 팔에서 `WARN_D1_IMU_INPUT_MISSING`이 0이다.

## 7. 실행 계획 (E코어 전용, 마스크 0x0FFF0000 = E 12개)

- 단가 근거: 같은 r79 경로 H-8 V0(`v5/resume_k1/h8_noise_V0.json`, E 8 작업자)의 실행당 wall은 중앙값 44.1 s, 최대 111 s다. 계획은 45 s/건, 작업자 12개로 잡는다.

| 단계 | 내용 | 건수 | 예상 wall |
|---|---|---|---|
| H0 | 동일성: R0 × identity 20키 × (L1, L2 s0) 대 r79 직접 실행 | 40 + 40 | 약 6분 |
| H1 | L1 × 7팔 × 129 | 903 | 약 57분 |
| H2 | L2 × 시드 0~2 × 7팔 × 129 | 2,709 | 약 2.8시간 |
| H3 | 감도 4팔 × 129 × L2 s0 | 516 | 약 33분 |
| 합계 | | 4,208 | **약 4.4시간**(CPU 약 53시간) |

- 순서: H0가 통과(해시 일치)하면 H1을 시작한다. H1 지표를 보고 H2로 간다(팔을 줄일 수 있다).
- Chrono SCM 확인(H4, 나중)
  - 저널 묶음이 끝난 뒤 P코어로 돌린다.
  - 6사례 × 3팔(R0, A-g, B-r) = 18건. 사례: J1 B 평지 상단, J2 B 평지 하단, G1 후방 약패드 RR, 강체 pitch +3° 상단, 강체 roll +4° 중단, J1 좌우 R_c 0.6.
  - 비용과 배치는 compute-scheduler가 정한다.

## 8. 가정

| 가정 | 값 | 비고 |
|---|---|---|
| 경사계 내부 필터·지연·분해능 | 2단 1 Hz, 20 ms, 0.01° | 제품 근거는 위임 1 |
| AHRS 교차·지연·분해능·시작 | 0.05 Hz(ζ 1, 바이어스 적분), 10 ms, 0.001°, 웜 | 0.05 Hz는 선형 해석이 요구하는 값 |
| 출력 주기 | 10 ms(둘 다) | |
| 오차 등급 | 기존 `IMU_GRADES`(가속도 영점·잡음, 자이로 ARW·바이어스) | 공통 난수 |
| A 이득 | Kp 0.12, Ki 0.006(Ki/Kp 유지), K_g 0.10 | 선형 기준만으로 고름 |
| 탐침 진리 문턱 | 실제 힘 > 1 kN = 접지 | M4 |
| 비교 범주 허용폭 | 5절 | 탐색용 범주 |
| 선형 모델 | R8 C2 루프만(LAS·SGS 등 논리 없음), 다리 α 미계산, 측정 강성 정규화 r = 1 | |

## 9. 실행 기록 (선형 해석)

- 스크립트(이제 `lin_evidence/`)
  - `imuatt_lin.py`(1차 26변형), `imuatt_lin2.py`(2차 23변형), `imuatt_summ.py`
  - `imuatt_probe.py`(3.1·4.2절 해석)
  - `imuatt_export_jl.py`, `imuatt_check.jl`·`run_check.jl`(Julia 독립 조립), `cmp_jl.py`
  - `imuatt_lin.py`의 `R8D1` 경로는 worktree `journal-v0`를 가리킨다. 다시 돌리려면 고쳐야 한다.
- 결과: `lin_full.json`·`lin_full_summary.json`(3,360건), `lin2.json`·`lin2_summary.json`(5,520건), `probe_calc.json`, `imuatt_export.json`, `imuatt_check_jl.json`.
- 교차 검증: Julia(julia-mcp, control-julia, Manifest 변경 없음)로 원 연속 행렬에서 센서 상태와 지연 버퍼를 다시 조립했다(20만 점 격자, 30사례).
  - 각 사례 지배 채널 $M_s$의 상대차 ≤ 1.3×10⁻⁵: **허용 일치**.
  - 비지배 채널 2건은 불일치했다. 둘 다 top_pads_b1.6_sup_lower 플랜트다.
    - S0 + 20 ms φ: Python 1.3930, Julia 1.4048
    - A 0.5 Hz 비틀림: 1.2220, 1.2288
  - 원인은 Python 봉우리 탐색이 좁은 봉우리를 놓친 것이다. 두 값 모두 지배값이 아니라서 판정은 바뀌지 않는다.

## 개정 1 (2026-11-22): 제품 조사 반영 (`sensor_product_survey_20261122.md`)

- **우선:** 0·2.2·3·4.2·6.3·7절의 값과 이 개정이 다르면 이 개정이 우선한다. 개정 1 기준 실행 건수는 H1 903 + H2 2,709 + H3 645 = **4,337건**이다.

- **A 경사계 기본 필터를 2차 Bessel 1 Hz로 바꾼다**(SOLAR-2 기본, ZOH 정확 이산화). 1차 2단 1 Hz는 감도 팔(A-g-2x1)로 남긴다.
  - 조사서는 "1차 2단이 위상 손실이 커서 보수 쪽"이라고 보았지만, 이 루프에서는 성립하지 않는다.
  - 지배 봉우리(로킹 공진 약 1.1 Hz)에서 2차 1 Hz 필터가 크기를 더 많이 통과시키기 때문이다. 현행 이득에서 Bessel은 2.316 / 가드 2.452, 1차 2단은 1.707 / 1.791이다.
- **A-g 이득을 Kp 0.10 s⁻¹, Ki 0.005 s⁻², K_g 0.08 s⁻¹로 바꾼다.** 원안(0.12 / 0.006 / 0.10)은 Bessel에서 1.521 / 1.546으로 미달한다.
  - 새 이득, Bessel 1 Hz: 1.400 / 1.452, PM 44.1°, GM 11.1 dB, 교차 주파수 0.062~0.111 rad/s(현행 대비 약 −42 %)
  - 같은 이득으로 다른 필터: Butterworth 1 Hz 1.412 / 1.455, Butterworth 5 Hz 1.330 / 1.357, 이동평균 200 ms(보수 대용) 1.465 / 1.481
  - τ_v 0.15일 때: 1.353 / 1.394
- **B AHRS 기본값을 바꾼다.** 교차 주파수 0.032 Hz(SICK 기본 5 s에 대응, 가정), 분해능 1×10⁻⁴ rad(0.0057°, SBG CAN). 지연은 10 ms 그대로 둔다(보수 쪽).
  - 선형 결과: τ_f 0.8에서 1.400 / 1.475, τ_f 0.4에서 1.224 / 1.430
- **4.2절의 "LSB ≤ 0.001°" 요구를 철회한다.**
  - 몬테카를로(R8 3점 창, Q1·Q1b, 10⁴회)에서 0.0057~0.01° 양자화는 기권을 오히려 줄였다(보통 등급 0.85 → 0.65~0.49, f_c 0.05 Hz 값; 채택한 0.032 Hz에서는 0.61~0.46).
  - 위험 쪽 오판은 이 해상도(약 3×10⁻⁴) 안에서 현행과 구별되지 않았다.
  - 탐침 단서 표본은 주기 평균으로 고정한다. 마지막 표본을 쓰면 위험 쪽 오판이 1.5×10⁻³으로 늘어난다.
- **소견(이 연구 범위 밖, 기록):** 같은 간이 모델에서 현행 자이로 단서도 보통 등급 84 %, 우수 등급 50 % 기권한다. 잔류 로킹이 0.003°만 있어도 99 % 넘게 기권한다(원인은 Q1b와 3점 창). 하네스 M4에서 R0의 기권률과 원인(Q1/Q1b)을 기록해 확인한다.
- **H3 감도 팔:** A-g-bw5, A-g-2x1, B-r-q10, B-r-cold, C-r(645건).
- **검증:** Julia 독립 조립(Bessel 계수도 독립 계산) 7사례에서 상대차 ≤ 5.6×10⁻⁵로, 허용 일치다.
- **근거 파일:** `rev1_evidence/`(SHA256SUMS). `imuatt_lin3.py`는 `lin_evidence/imuatt_lin.py`를 import하므로, 다시 돌리려면 경로를 고쳐야 한다.
- **구현 변경(python, H0 전)**
  1. `internal_filter`(bessel2 / butter2 / first_order_x2, 기본 bessel2). 2차 필터는 ZOH 정확 이산화, scipy 계수 대조.
  2. AHRS `complementary_hz` 기본값 0.032.
  3. AHRS `resolution_rad` 기본값 1×10⁻⁴.
  4. 탐침 단서 표본은 주기 평균.
  5. A-g 이득 0.10 / 0.005 / 0.08.
  6. H3 팔 교체.
  7. 지연은 그대로.
  8. M4에 `attitude_ripple_ratio`·`attitude_drift_ratio`와 기권 원인을 기록(모든 팔).