# 판 8 K1 창 재정의 설계 (control-expert, 2026-11-26)

## 0. 판정·요약
**검증 판정: 일치**(비틀림 루프 여유, Python ↔ Julia). 사양 미달 없음(가정한 사양: PM ≥ 45°, GM ≥ 6 dB, $M_s$ ≤ 2.0).

| 항목 | 결과 |
|---|---|
| 원인 | K1 mid 읽기가 명령 횟수(5/10주기)로 고정돼 있다(`ground_contact.py` 991~993). 그 읽기 때 실이 고착이면 실 띠가 창에 들어간다(dynamics D-1) |
| 후보 | (a) 이동 확인 mid, (b) 미끄럼 구간 회귀, (c) 고착 다리 제외. (a)는 통합형(모든 K1 쓰임)과 분리형(스케일·경고만) 두 꼴 |
| 오프라인 재생 | 재실행 23줄(a2 12, A 11), 1회차는 정확. (a) δ 0.05 mm 분리형: 방향 A 경고 라운드 3 → 0, a2 10 → 0, 잔여 띠 최대 1.52 → 0.27 $S_{ii}$. (b)(c)는 스케일 다리 수가 3 미만인 라운드가 대부분이 되어 버림 |
| 명령 영향 | 분리형은 F_band·하중 추정 경로를 바꾸지 않는다. 스케일이 바뀐 라운드는 방향 A 1/19(1회차 0/11), a2 6/23. 상한 클램프 1.5를 넘던 값이 1.5 아래로 내려오는 라운드에서만 이득이 바뀐다 |
| 경고 상한 | 2.3 → **3.6**(이웃 실 고착 강체 손계산 최대 3.53, 재생 최대 2.08, 비틀림 루프 원비 3.6에서 PM 66.6°) |
| 권고 | **(a) 분리형 PSW, δ = 0.05 mm, 경고 (0.8, 3.6)** |

## 1. 지금의 코드 경로(ed8-impl 7fc83456, 읽기만)
- mid 읽기: `_step_trapezoid`에서 `len(sent_speeds) == len(trapezoid)//2`일 때(6번째 명령을 보내기 전) `_record_mid_reading`(`ground_contact.py` 991~993, 1126~1130). 사다리꼴 10주기(`trapezoid_speeds` 665~698: 깊이 2 mm, D 0.56 s, τ 0.36 s), 명령 1.14 mm 시점.
- K1 = $(F_{ext}-F_{mid})/(x_{ext}-x_{mid})$, $x$ = 피스톤 판독 `rod_stroke_m`(`ProbeReading` 356). `_stiffness_cue` 600~610. ext = 첫 이동 뒤 유지 끝 읽기(`_end_stage` 1140~1147).
- K1의 쓰임 셋
  1. 강성 접지 $K1>0.3S_{ii}$(611) → 결합 판정(507~510)
  2. MEASURED_IF_GROUNDED 보정(`c2.py` 1688~1693, 2537): 하중 추정 $0.5(E+R)-0.5K1(s_E-s_R)$, 실 마찰 추정 $0.5(E-R-K1(s_E-s_R))$(612~622) → F_band(`c2.py` 9874~9890), 재접지 판단
  3. 비틀림 스케일: 스케일 다리(`c2.py` 3093~3097) ≥ 3이면 중앙값 원비, 경고 (0.8, 2.3), 클램프 [1.0, 1.5](9892~9925). 이득 = $K_{tw}/(k_{nom}\sigma)$(3817~3853, 7721~7734)
- 판정서의 "1.5에서 잘려 영향 없음"은 쓰임 3만 본 말이다. 쓰임 2도 K1을 쓴다.

## 2. 후보
| 후보 | 정의(사다리꼴 첫 이동) | 실기 적용성 |
|---|---|---|
| (a) 이동 확인 mid | mid = max(지금 mid, 첫 이동 시작 읽기 대비 피스톤 판독 이동 ≥ δ인 첫 읽기), ext 읽기 전. mid → ext 이동 < 0.2 mm면 NaN | 피스톤 판독만 씀 → 그대로 적용. δ는 판독 잡음 $\sigma_x$로 $\max(0.05,3\sqrt2\sigma_x)$ mm. 잡음이 δ보다 크면 mid가 일찍 잡혀 지금과 같아질 뿐(해 없음). 실의 유한 예비 미끄럼은 띠 일부를 남김 |
| (b) 미끄럼 구간 회귀 | 지금 창의 읽기 구간 중 $dx>0$이고 $dF/dx<0.5k_h$인 구간만 합산 | $k_h(s)$(β·사체적 미확인) 필요, 10 Hz 구간 이동 0.1~0.3 mm라 잡음에 약함 |
| (c) 고착 다리 제외 | mid까지 이동 < δ면 그 다리 K1 = NaN(스케일에서 뺌) | 적용 가능하나 다리 수가 줄어듦 |
- (a)는 두 꼴: **통합형**(K1의 세 쓰임 모두) / **분리형**(쓰임 3만, 쓰임 1·2는 지금 K1).

## 3. 오프라인 재생(사전 효과)
### 3.1 방법
- 입력: `ed8_design/dynamics_d1_d3/rerun_raw/logs/<run>_{ctrl.npz, plant.npz, cue.json}` 23줄(판 7 실행 커밋 C 8a2a52ce, a2 = 판 7 봉인, A = (i-b) 끔·증인 판정 켬 = 구현 a2w).
- 제어기 로그의 10 Hz 읽기(`s.last_reading.cylinder_force_N`·`rod_stroke_m`)로 다리별 창을 다시 만들었다. mid 읽기는 cue의 `first_move_mid_force_N`(|차| < 1 N)로 찾고 첫 명령 결정 읽기 = mid − 5주기로 뒀다(로그 `cmd`는 지연된 출력일 수 있어 k03에서 확인).
- 확인: 지금 창 K1이 cue `stiffness_N_m`와 상대차 ≤ 1e-6인 다리 136/138(나머지 2개는 Mh15-a2 2회차, 0.4 %·7e-6, 같은 힘 값 중복 매칭). cue가 없는 다리 9개는 뺐다(`k02_summary.json`).
- 진값: 플랜트 로그의 실 힘 $f$로 $K_{pad}=(\Delta F+\Delta f)/\Delta x$, 잔여 띠 $(K1-K_{pad})/S_{ii}$.
- 1회차는 정확하다(K1은 라운드가 끝난 뒤에만 쓰임, `c2.py` 9822~9837). 2회차 이후는 옛 제어기 궤적 위의 근사다.

### 3.2 결과(`k05_out.txt`, 원비 = 중앙값, 정의 = 스케일 다리 ≥ 3인 라운드)
| 팔 | 후보 | 정의 라운드 | 경고(0.8, 2.3) | 최대 | 스케일 다른 라운드(1회차) | F_band 원천 변화 최대 [kN] | 잔여 띠 최대 [$S_{ii}$] |
|---|---|---|---|---|---|---|---|
| a2(23 라운드) | 지금 | 13 | 10(높음 9, 낮음 1) | 3.472 | – | – | 2.137 |
| | (a) δ 0.02 | 12 | 0 | 1.825 | 6(3) | 2.39 | 0.259 |
| | **(a) δ 0.05** | 12 | 0 | 1.665 | 6(3) | 2.62(통합형) / **0(분리형)** | 0.259 |
| | (a) δ 0.1 | 12 | 0 | 1.665 | 7(4) | 2.62 / 0 | 0.272 |
| | (b) | 2 | 0 | 0.965 | 13(7) | 3.62 | – |
| | (c) δ 0.1 | 1 | 0 | 1.533 | 13(7) | 2.62 | – |
| A(19 라운드) | 지금 | 13 | 3 | 2.866 | – | – | 1.522 |
| | (a) δ 0.02 | 13 | 0 | 2.187 | 1(0) | 0.43 / 0 | 0.265 |
| | **(a) δ 0.05** | 13 | 0 | 2.083 | **1(0)** | 0.43 / **0** | 0.265 |
| | (a) δ 0.1 | 13 | 0 | 1.924 | 4(2) | 0.94 / 0 | 0.300 |
| | (b) | 5 | 3(낮음) | 1.062 | 13(7) | 1.08 | – |
| | (c) δ 0.1 | 2 | 0 | 1.583 | 12(6) | 0.45 | – |
| A | 진값 $K_{pad}$(지금 창) | 13 | 2(Mh15 2.454·2.510) | 2.510 | – | – | 0 |

- 방향 A 줄별(지금 → (a) δ 0.05): Mh15 Fs8 2.734·2.866(경고) → 1.771·1.529, Mslow Fs8 2.239·2.468(경고) → 1.827·1.836, M Fs8 2.083·2.187 → 2.083·1.924, L Fs8 2.083·2.036 → 2.083·1.907, R7 2.047 → 2.007, Mslow FL-Fs0 1.416·1.389 → 1.416·**1.099**, LSM4 FR-Fs0 1.583·1.703 → 같음. S7 줄은 두 창 모두 정의 안 됨.
- 스케일이 바뀐 방향 A 라운드는 Mslow FL-Fs0 2회차(1.389 → 1.099, 근사 라운드) 하나다. 비틀림·가드 이득이 1.26배 커진다.
- (a) 통합형은 고착 다리의 실 마찰 추정을 키운다(M-a2 FR 8.74 → 13.89 kN, 진값 $F_s$ 8 kN). 그래서 F_band가 12.8 → 14.9 kN으로 바뀌어 하한·재접지 경로까지 명령이 바뀐다. 분리형은 이 경로를 건드리지 않는다.
- 낮은 끝: a2 S7 Mslow 2회차 0.589(경고)는 (a)에서 스케일 다리 0이 되어 정의되지 않는다(이전 스케일 유지, 경고 없음).

### 3.3 δ 선택
- δ 0.02~0.1은 경고를 모두 없앤다. δ가 클수록 이미 미끄러지던 다리의 mid도 늦어져(방향 A mid 이동 다리 10 → 21 → 33) 창 위치 효과로 원비가 내려간다. 0.1에서 스케일 바뀐 라운드가 4로 는다.
- a2 팔에서 "새 mid에서도 고착"인 다리는 δ 0.02·0.05에서 4, 0.1에서 0이다(부분 미끄럼 뒤 재고착). 방향 A에서는 모두 0이다.
- **δ = 0.05 mm**를 고른다. 방향 A에서 발자국이 가장 작은 쪽(0.02와 같음)이면서, 하네스 고착 다리 이동이 정확히 0인 것과 수치 잔류를 떼어 둘 만큼 크다. 결과 본 뒤 선택이다(명세 O8-3).

## 4. 명령 영향(권고안)
- 쓰임 1·2(접지 판정, 하중·실 마찰 보정, F_band): 바뀌지 않는다.
- 쓰임 3(스케일): 옛 중앙값과 새 중앙값이 둘 다 ≥ 1.5면 클램프 때문에 이득이 같다. Fs8 강체 줄 대부분이 여기다. 바뀌는 곳은 새 값이 1.5 아래로 내려오는 라운드와 $F_s$ 0 계열(1.1~1.5)이다. 하한 1.0은 재생에서 건드리지 않았다(최소 1.099).
- 스케일 다리 수가 3 미만이 되면 이전 스케일(첫 라운드면 탐침 전 1.2)을 쓴다. 재생에서 방향 A 정의 라운드 수는 13 → 13으로 같았다.
- 결론: 명령은 일부 줄에서만 바뀐다. census가 실제 크기를 정한다.

## 5. 경고 상한 근거
### 5.1 물리 범위(손계산, 가정: 3자유도 강체 지지)
- 균일 강성 $k$에서 $S_{ii}=k\,n_i^2$, 비틀림 강성 $=k$(`attitude_sensitivity_rad_m` 439~453과 같은 모형).
- 이웃 셋이 고착(다리 강성 = 패드 $k_s$, 전방 216.6·후방 205.1 MN/m)이고 탐침 다리는 미끄럼($k_{n,L1}$ 전방 25.9·후방 19.5)일 때 $S_{ii}=n_i^2/\sum_j n_j^2/k_j$
  - 전방 탐침 18.19 MN/m → /5.146 = **3.53**
  - 후방 탐침 15.67 MN/m → /6.207 = **2.52**
- 하네스는 이 모형보다 뻣뻣할 수 있다(dynamics 7절: $F_s$ 0 실측 1.06~1.90 대 모형 1.13~1.34. 옛 창 K_pad 후방 3.37 관측).
- 그래서 상한 2.3은 $F_s$ 8 kN 물리를 덮지 못하고, 3.6은 3다리 중앙값의 강체 상한(3.53)을 덮는다.

### 5.2 비틀림 루프 여유
- 모형(이산, $T_s$ 0.1 s, 음되먹임): $L(z)=g\,K_{tw}\,z^{-1}\,\mathrm{ZOH}\{1/(s(\tau_vs+1))\}\,\dfrac{0.5z}{z-0.5}$

| 기호 | 정의 | 값·출처 |
|---|---|---|
| $g$ | 원비 / 스케일 $r/\sigma$ | – |
| $K_{tw}$ | 비틀림 이득 | 0.5 s⁻¹(`c2.py` 1519~1524) |
| $\tau_v$ | 밸브 지연 | 0.1 s(하네스 `harness_hydraulics.py` 101, 실기 가정 U-R8-9) |
| 0.5z/(z−0.5) | 비틀림 하중 1차 저역(전진 오일러, T/τ = 0.1/0.2) | `c2.py` 1527·4682~4684, `sensors/attitude.py` 43~77 |
| $z^{-1}$ | 출력 지연 $d$ = 1 | `c2.py` 1628 |
- 데드밴드 2 kN·가드·잠긴 다리 불감대는 뺀 선형 소신호 모형이다.

| 경우 | $g$ | GM | PM @ $\omega_{gc}$ | 지연 여유 | $M_s$ | 최대 \|z\|(폐루프) |
|---|---|---|---|---|---|---|
| 공칭 $r$ 1, σ 1 | 1.000 | 13.11(22.35 dB) @ 4.837 rad/s(0.770 Hz) | 80.02° @ 0.498 rad/s(0.0793 Hz) | 2.80 s | 1.151 | 0.939 |
| $r$ 2.3, σ 1.5 | 1.533 | 8.55(18.64 dB) @ 4.837 | 74.79° @ 0.760 rad/s(0.121 Hz) | 1.72 s | 1.235 | 0.888 |
| **$r$ 3.6, σ 1.5** | 2.400 | **5.46(14.75 dB)** @ 4.837 | **66.56°** @ 1.175 rad/s(0.187 Hz) | 0.99 s | **1.383** | 0.816 |
- 한계(이분법): PM 45°는 $g$ ≤ 4.94(σ 1.5에서 $r$ 7.41), GM 6 dB는 $g$ ≤ 6.57($r$ 9.85), $M_s$ 2는 $g$ ≤ 5.03($r$ 7.54). 안정 한계는 탐색 범위 끝($g$ 8) 밖이다.
- **두 경로 대조**

| 양 | Python(`ctrl_verify.py margins`, 조밀 격자) | Julia(ControlSystemsBase `margin`, 20만 점) | 상대차 | 판정 |
|---|---|---|---|---|
| GM($r$ 3.6) | 5.461343280183603 | 5.461343280732118 | 1.0e-10 | 일치 |
| PM | 66.55889884790162° | 66.55889884167387° | 9.4e-11 | 일치 |
| $\omega_{gc}$ | 1.1750412646366664 | 1.175041264952095 | 2.7e-10 | 일치 |
| $M_s$ | 1.383254641657912 | 1.3832546415699611 | 6.4e-11 | 일치 |
| 폐루프 극 | 0.80782 ± 0.11742j, 0.25225, 0 | 0.80782 ± 0.11742j, 0.25225 | ≈ 1e-15(공통 극) | 일치(아래 비고) |
- 비고 1: `compare`는 극 집합 크기 4 대 3으로 불일치를 냈다. Python 쪽의 z = 0은 필터 분자 $z$와 지연 $z^{-1}$이 상쇄된 극이다(Julia `minreal` 전후 모두 3극). 공통 3극은 값이 같다.
- 비고 2: python-control `stability_margins`는 frd 방법으로 넘어가 공칭·$r$ 2.3에서 이득 교차를 놓쳤다(도구 cross_check 불일치, 알려진 함정). 정답은 격자와 Julia로 판단했다. 공칭·$r$ 2.3도 Python 격자와 Julia가 같은 값이다(k06·k07 출력).
- 결론: 상한 3.6 안에서는 비틀림 루프 여유가 충분하다. 상한은 안정 한계가 아니라 "측정이 물리적으로 그럴듯한 범위"의 경계다.

## 6. J7 취급
- `WARN_PROBE_STIFFNESS_OUT_OF_RANGE`: 규칙은 판 7과 같다(j9_main은 실패로 셈, 감도는 단독 조건 예외). 원인(창 산물)을 제어기에서 고쳤고 상한을 물리 범위로 옮겼으므로, 판정 완화는 하지 않는다. 공개: 경고 범위 변경은 판 7 결과 본 뒤의 제어기 변경이다.
- `WARN_PROBE_RETRACT_NOT_OPENED`(방향 A)
  - R2(권고): 증인 기록 전용이면 사건을 내지 않는다(기록 키만). J7 질문이 없다.
  - R1(a2w): 사건이 난다(dynamics: VBMslow R12 top-FL-Fs0 네 다리). (가) Q7-C4 유지 → census에서 VBNslow J7 실패 가능성이 크다. (나) J7에서 빼고 기록 → 결과 본 뒤 완화, 공개 문구: "방향 A에서 거울 수축은 열림을 보장하지 않도록 설계했고, 이 경고는 실기 증인이 아니며(실기 변위 증인 불성립, Q7-H6), D6는 증인 판정 모드에서 이미 그 라운드를 판정 불가로 둔다. 그래서 J7 실패에서 빼고 수를 기록한다(판 7 Q7-C4를 결과 본 뒤 뒤집음)."

## 7. 권고안
- **(a) 분리형 PSW**: 스케일·경고용 K1만 "첫 이동 시작 대비 피스톤 판독 이동 ≥ 0.05 mm가 확인된 첫 읽기(지금 mid 이상, ext 전)"부터 ext까지로 잰다. 접지 판정·하중 보정 K1은 그대로. 경고 (0.8, 3.6).
- 버린 것: (a) 통합형(F_band 경로 변경, 실 마찰 과대 추정), (b)(스케일 다리 부족, 낮은 끝 경고, $k_h$ 필요), (c)(스케일 다리 부족으로 탐침 전 스케일로 되돌아감).

## 8. 위임 필요(python-expert): 구현 명세
대상 브랜치 ed8-impl(7fc83456 위). 실행 커밋·판정 커밋 분리는 명세 11절.
- **Y8-1 PSW**
  1. `ProbeSettings`에 `scale_mid_min_piston_travel_m: float | None = None`(None = 꺼짐) 추가. 판 8 설정만 `0.05e-3`.
  2. `_LegRecord`에 `start_rod_stroke_m`(그 다리 첫 탐침 주기 읽기의 `rod_stroke_m`, `start_motor_stroke_m`을 정하는 904행과 같은 곳), `scale_mid_force_N`·`scale_mid_rod_stroke_m`(NaN), `scale_mid_shift_periods`(None) 추가.
  3. `_step_trapezoid`: FIRST_MOVE 단계의 각 읽기에서, 지금 mid가 이미 기록됐거나 이 읽기에서 기록된 뒤(991~993 다음 줄), 스케일 mid가 없고 `first_sign*(rod − start_rod) >= δ`면 이 읽기를 스케일 mid로 기록한다. 유지 구간 읽기도 후보다. 첫 이동을 끝내는 읽기(`_end_stage`가 FIRST_MOVE를 끝내는 읽기 = ext)는 후보가 아니다. `_step_rect`는 바꾸지 않는다.
  4. `ProbeSample`에 `scale_mid_force_N`·`scale_mid_rod_stroke_m`(NaN 기본) 추가, `_evaluate` 1203~1204 옆에서 채움.
  5. `_stiffness_cue`가 `scale_stiffness_N_m`도 낸다: 설정 None → K1과 같음 / 지금 mid NaN → K1 / 스케일 mid NaN → NaN / `first_sign*(first_rod − scale_mid_rod) < min_travel_m` → NaN / 그 밖 → `(first_force − scale_mid_force)/(first_rod − scale_mid_rod)`. K1·접지·보정 계산(600~622)은 바꾸지 않는다.
  6. `ProbeResult`에 `scale_stiffness_N_m: float = math.nan`, `scale_mid_shift_periods: int | None = None`.
  7. `c2._update_twist_stiffness_scale`: 설정이 켜지면 원비 다리 = `_is_stiffness_scale_leg(result)` ∧ `scale_stiffness_N_m` 유한 ∧ `scale_stiffness_N_m > probe.grounded_stiffness_ratio * load_sensitivity_diag_N_m[leg]`, 원비 = `scale_stiffness_N_m / nominal[leg]`. 꺼지면 지금 코드 그대로.
  8. P-1 기록(`_record_probe_stiffness`)에 다리별 `scale_k_N_m`, `scale_ratio`, `scale_mid_shift_periods`, `moved_by_mid_m`(지금 mid 때 이동), `is_psw_scale_leg`를 더한다(명령 불변).
- **Y8-2 경고 범위와 설정**: 판 8 설정의 `R8Settings.stiffness_warning_range` = (0.8, 3.6). 클래스 기본·`R8_D1_SETTINGS`·기존 프리셋 값은 바꾸지 않는다. 판 8 설정 이름(초안) `VBN`, `VBN0`, `LSN1`~`LSN4`, `VBNslow`·`VBNfast`·`VBNc005`·`VBNc04`·`VBNb069`·`VBNb16`·`VBNh05`·`VBNh15`·`VBNd05`·`VBNd15`, `VBKN`·`VBKN0`. 태그(초안) `final_C4G2_P3X_LAS_K1_LSB_PSW` / VBN0 `final_C4G2_LAS_K1_LSB_PSW`; `extend_start_revision_of_tag`가 rev 7을 주는지, `is_extend_start_tag`가 맞게 판별하는지 시험. meta `probe_k1_scale_settings`. `ed8_probe.py`에 판 8 팔(이름 제안 `a8`) = (i-b) 끔 + 증인 방식(Q8-1) + PSW + 경고 (0.8, 3.6).
- **Y8-3 증인 기록 전용(R2, Q8-1 확정 뒤)**: `ProbeD6Settings`에 `witness_mode: "judge" | "record"`(기본 `"judge"` = 판 7 동작). `"record"`면 `probe_round_finished`가 판 6 규칙(witness 없음 경로)으로 D6를 판정하고, 증인 라운드 값은 `d6_witness` 기록에만 남긴다. `INFO_D6_NOT_OPENED`·`WARN_PROBE_RETRACT_NOT_OPENED` 사건은 내지 않고 다리별 `not_opened_rounds`, `would_warn` 기록.
- **Y8-4 기록 키**(3.5): A(i) 끝 사유·바닥 최대, 완료 플래그 분해, 잠긴 다리 명령. 명령 불변.
- **Y8-5 토큰 충돌 점검**: 새 이름·`_PSW`를 `03_src`·`04_scripts`·`05_tests`·`00_docs`·`02_params`에서(판 7 Q7-C3 꼴).
- **Y8-6 키 파일**: `census_keys_ed8.json`(명세 5.1의 4단 1043줄, 각 줄 `stage`·`job`·`setting`·`v0_pair`), `heldout_g_ed8.json`(7.2 규칙, seed는 명세 값). `generation_command`의 경로 의존(판 7 5.1)을 피하려고 `lines` 비교 시험을 둔다.
- **옛 설정 명령 불변(P8-0)**: 모든 기존 설정(VBM 계열 포함)의 `commands_sha256`이 판 7 C와 같아야 한다. 시험: 7fc83456의 8 job 대조 유지 + `ed7_probe.py --arms a2 --part all` 114줄 해시(기대 b46bdf8f 재현 줄별 해시). PSW 설정 None·`witness_mode="judge"`면 새 코드 줄이 하나도 돌지 않음을 단위 시험으로.
- **P8-5·P8-6 시험**: PSW 꺼짐 동일성, 스케일 mid가 옮겨지지 않은 라운드만 있는 합성 줄의 동일성. 1회차 $K1_{sc}$가 `control_k1_window/k02_legs.csv`의 `a0.05_k1`(방향 A 행)과 상대차 ≤ 1e-9(하네스 시험, 키 R12 top-FR-Fs8 o0.0 × {M, Mslow, Mh15, L}, R7 e0.0 × M).
- 단위 시험: 고착 읽기(이동 0.000 mm 3주기) 뒤 이동하는 합성 읽기에서 스케일 mid가 늦어지고 K1(접지·보정)은 그대로인지, 역순(첫 이동 수축)에서 부호, ext 읽기만 후보인 경우 NaN, 사각 프로필에서 $K1_{sc}=K1$.

## 9. 가정과 한계
| 구분 | 내용 |
|---|---|
| 가정 | 사양 PM ≥ 45°, GM ≥ 6 dB, $M_s$ ≤ 2.0(고전 관례, 프로젝트 사양 아님) |
| 가정 | $\tau_v$ 0.1 s(하네스 값), 실기 미확인(U-R8-9) |
| 가정 | 강체 3자유도 지지 손계산(패드 $k_s$, $k_{n,L1}$은 dynamics 보고 값) |
| 가정 | δ 실기 값은 판독 잡음 $\sigma_x$로 다시 정함(프로젝트는 R8 영점 복귀 허용에서 $\sigma_x$ 0.1 mm를 가정, `c2.py` 1532~1534) |
| 한계 | 재생 23줄, 방향 A 11줄뿐. 2회차 이후는 근사. 감도 h05·b069·d05 등은 재생하지 않음 |
| 한계 | 판정 T4h에는 피스톤 판독이 없어(hydraulics 5절) 판 7 저장 j9_main·감도 848줄로 넓히지 못함. census가 실측한다 |
| 한계 | 비틀림 루프 여유는 선형 모형(데드밴드·가드·잠긴 다리 불감대·자세 루프 결합 제외) |
| 한계 | 분리형은 접지·보정 K1의 창 산물을 남긴다(실 마찰 추정이 작게 나오는 쪽, 명세 13절 4) |

## 10. 수행한 작업
- 실행: PowerShell에서 `conda run -n dynamics-dev python -I -B <스크립트>`(`MKL_THREADING_LAYER=TBB`), Julia는 julia-mcp `run_file`·`eval_code`(project `C:\Users\jinbeom\.claude\tools\control-julia`, 첫 호출 21 s, 세션 닫음).
- 출력 폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_k1_window\`

| 파일 | 내용 |
|---|---|
| `k00_inspect.py` → `k00_out.txt` | 원자료 키 |
| `k01_inspect_ctrl.py` → `k01_out.txt` | 제어기 로그 키·cue |
| `k02_replay.py` → `k02_legs.csv`, `k02_rounds.csv`, `k02_summary.json` | 창 후보 재생 |
| `k03_debug_fr.py` → `k03_out.txt` | M-a2 FR 1회차 10 Hz 추적 |
| `k04_tables.py` → `k04_out.txt` | 표 |
| `k05_summary.py` → `k05_summary.json`, `k05_out.txt` | 팔별 후보 요약 |
| `k06_twist_margins.py` → `k06_margins.json`, `k06_out.txt`, `loops/loop_*.json` | 비틀림 루프 여유(Python) |
| `k07_twist_margins.jl` → `loops/jl_*.json` | Julia 경로 |
| `loops/py_*.json`, `loops/cmp_*.md` | `ctrl_verify.py margins`·`compare` 출력 |
| `provenance.json` | 열 정의(정의식·코드 줄·단위·창), 입력, 정확도 |
- SHA256SUMS는 만들지 않았다(메인이 고정할 때).
- worktree는 읽기만 했고 고치지 않았다. 커밋하지 않았다. scratchpad `control-ed8\`은 지웠다(Julia 스크립트는 프로젝트 폴더로 옮김).

## 11. 공개(행위 그대로)
- 블라인드 경로(606f8713 `cdry_a1\VBK_c92*`·`VBK_c93*`·`logs\`와 worktree 사본, 판 6 `x11\selection.json`)는 열지도 검색하지도 않았다. `j9_runs` 아래에는 어떤 도구로도 접근하지 않았다.
- Glob은 `ed8_design`, `ed8_design\python_p1_p3`, `ed8_design\dynamics_d1_d3`, `C:\Users\jinbeom\.claude\tools\control`에만 썼다.
- Grep: 명세 v7 파일 하나, decision_log 파일 하나, worktree `03_src\outrigger_sim`·`03_src\outrigger_sim\control`·`04_scripts\04_hydraulic\coupled`(glob `*.py` 또는 파일 지정), worktree `04_scripts` 자체 1회(glob `*.py`, 출력 .py 3줄; 명세 O8-6).
- 읽은 자료: 판 7 판정서, 원인 분석, dynamics·hydraulics·stats·python 보고, 명세 v7 1~120·228~1108행, decision_log 823~824행, worktree 코드(provenance `code_read`).

---
**의존성 점검:** depcheck control-expert OK(control·slycot·scipy·sympy·cvxpy·casadi 등, sysidentpy 0.9.0, julia·control-julia). 스모크 점검은 생략했다(이번 계산은 `ctrl_verify.py`와 Julia 대조로 두 경로를 직접 확인).

**확인 필요**(명세 15절과 같음): Q8-1 증인 기록 전용 방식(R2 권고), Q8-2 G1 171줄 census 포함(권고), Q8-3 문턱(stats), Q8-4 하네스 seed, Q8-5 이름·태그, Q8-6 경고 상한 3.6, Q8-7 R1이면 RETRACT WARN J7 취급, Q8-8 기록 팔 없음.

**위임 필요**
- python-expert: 8절 Y8-1~Y8-6, P8-0·P8-5·P8-6 시험, 하네스 seed 효과 확인(Q8-4).
- stats-design-expert: 명세 `<S8R_CENSUS_*>`·`<S8R_HO_*>`·`<S8R_P0_UB_MAX>` 검토, census에서 군집 규칙을 빼는 것과 층별 허용 수.
- dynamics-expert(진행 중 결과 대기): `<S8R_O00_RULE>`·`<S8R_U832_RULE>`·`<S8R_O00_NEW_ROWS>`.
- verif-protocol-auditor: S8-R 봉인 전 감사(T축: S8-R 봉인이 census보다 앞서는지, G′ 처리 팔이 S8-C 전에 돌지 않는지, 병합·별칭 규칙이 도구와 같은지).

**메인 세션 권고:** 긴 실행 없음. census는 S8-R·C8·T8 뒤 1043줄(줄당 약 170 s, 8 worker면 약 6시간, compute-scheduler-expert 배치표). G′ V0 사전 실행은 약 2 × 171줄.

사용한 스킬: 없음
