# Chrono 모델 단계별 구축 계획 (2026-10-19, 개정 11: 2026-10-20)

작성: cad-expert. **계획 문서다.** S0 공통 기반 일부(파라미터 로더, 좌표·신호 타입, SimEngine 프로토콜, Chrono 시스템 팩토리, 기준값 키 상수와 단위·엔진 규약 시험; 3.1절 "있음")만 만들어져 있고 물리 모델(바디·접촉·구동기)·실행기·시나리오 코드는 아직 없다.

개정 11(2026-10-20, dynamics-expert 편집): **S2a 최종 재판정(안 A) 통과**와 Δt 2×10⁻⁴ s 조건 ① 판정(근거 `00_docs/01_dynamics/dynamics_model.md` 개정 14, 5.5절).
- **S2a 통과(최종, 안 A)**: V7 1·2·3차 1.79818 / 3.00439 / 5.81472 Hz(rev13 기준 −0.007 / −0.010 / −0.075 %; 3차 차는 기준 `f_damped_Hz` = $\lvert\lambda\rvert/2\pi$와 맞춤 $f_d$의 정의 차 $\zeta^2/2$), ζ 보정 0.0078316 / 0.0139917 / 0.0372015 → 진단 ① 정상, $c_t/2$ 재확인, 부싱 이동 확인(개정 12 Chrono 대비 +0.70 / +0.63 %). V12 Chrono − 기준 = P-δ만(rev13 기대 차와 ≤ 0.63 N), 독립 비선형(볼 중심)과 ≤ 0.66 N. hold 해제 74.1~75.8 ms, hold 중 최대 접선력 ≤ 3.2 N. V13 통과.
- S1 재실행: 개정 8 판정 그대로 유효(변화 ≤ 0.16 N, cross_top 접선 예하중 +1.8~+7.7 %, 합 ≤ 2 N).
- **Δt 2×10⁻⁴ s 조건 ① 충족**: V7 yaw Δt 연구의 ζ₃ 기울기 = 예측 $r_3\omega_3/2$의 0.999배, 2Δt/Δt 비 2.000, 절편 = 기준 물리 ζ. 조건 ②와 함께 **2×10⁻⁴ s 전환은 사용자 결정 대기**(문안 `dynamics_model.md` 5.5절, YAML 그대로). S3 V8(a)는 에너지 비증가·1~6차 상한 판정으로 줄이고 Δt 1×10⁻⁴·2×10⁻⁴ s 두 개로 돈다.
- 스냅숏 작용점 방침(다르면 복원 거부, 변환 없음) 타당.
- 고친 곳: S2a 체크리스트, S3 위험 ①-2·체크리스트(V8(a)·결정 대기).

개정 10(2026-10-20, dynamics-expert 편집): **사용자 결정 안 A — L1 지면 부싱 작용점을 볼 중심으로 이동**(근거 `00_docs/01_dynamics/dynamics_model.md` 개정 13, 5.3절 ④·5.4절). 기준값은 `reference.json`에 키를 **더하기만** 했다(기존 키는 이력, 비트 단위 불변).
- **L1 V7 기준 키 변경**: `… / levels / <level> / V7_ball_centre_bushing_rev13` 아래 `f_undamped_Hz`, `f_damped_Hz`, `zeta`, `mode_shapes`, `zeta_num_r_omega_dt_half`, `V7_diagnostic / thresholds`. 상단 1~6차 1.7983 / 3.0047 / 5.8191 / 6.4218 / 7.6068 / 7.9995 Hz(이력 대비 +0.77 / +0.69 / −0.23 / −0.58 / −0.10 / −0.53 %), ζ 0.00783 / 0.0140 / 0.0372 / 0.0362 / 0.0323 / 0.0491. 진단 문턱은 ④만 0.0165 → 0.0162, 빼는 수치 감쇠 6.4×10⁻⁵ / 2.4×10⁻⁴ / 1.81×10⁻³.
- **V12 기준값(`slope_V12 / <case> / L1`)은 그대로**. 안 A 뒤 기대 Chrono − 기준 = P-δ만(수직 +68 / +51 / −52 / −67 N, 수평 ≤ 5 N): `reference.json / slope_V12 / <case> / L1_plan_A_expected_chrono_minus_reference_rev13`. 재실행 진단: 다리별 ≤ 3 N이면 부싱 이동 + P-δ로 설명됨(판정 허용은 그대로). 반올림 없는 신장 `extension_exact_m`·`extension_sphere_touch_m` 추가.
- 고친 곳: S2a 입력 키·V7 진단 행·V12 행·체크리스트, S3 V8(a) 행, S4 V7 행·β 판정 값, S5 V10 행. 이 백틱 경로들의 상수는 `verify/reference.py`에 아직 없다(python-expert가 더함, R12 시험은 그때까지 실패).

개정 9(2026-10-20, dynamics-expert 편집): **S2a 최종 판정(통과)** 과 판단 ①~⑥을 반영했다(근거 `00_docs/01_dynamics/dynamics_model.md` 개정 12, 5.3절).
- **S2a 통과(최종)**: V7(1차 1.78575 Hz·ζ 0.007774, 2차 2.98556 Hz·ζ 0.013894 → 진단 ① 정상, 3차 yaw 5.82728 Hz·ζ 0.037296으로 부싱 감쇠 입력 $c_t/2$ 확정), V12 3경우, V13.
- **V12 수직 차(최대 +295 / −281 N) = P-δ + 구 지렛대**: 독립 경사 바닥 비선형 정역학(`04_scripts/01_dynamics/run_s2a_slope_pdelta_check.py` → `06_analysis/00_dynamics/s2a_slope_pdelta_check.json`)이 Chrono를 ≤ 1.2 N로 재현한다. 구 지렛대는 부싱 접선력이 볼 중심 아래 0.06 m(구 접촉점)에 걸려 생기는 Chrono 구 패드 모델 오차다(실제 스위블은 합력이 볼 중심을 지남). 2°에서 ≤ 0.23 kN이라 허용 안이다. **부싱 작용점을 볼 중심으로 옮기는 안 A는 사용자 결정 대기**다.
- 초기 hold 규약(`attach(hold_until_loaded=True)`) 승인(조건: 간극 0 + 하중 0 출발에만, 램프 끝까지 미해제 다리가 있으면 실패 처리 — 코드 반영 위임). 정확한 접면 신장 수용. V12 탄성 변위 = 면내력/$k_t$(pitch 2° FL 0.396 mm)로 `dynamics_model.md` V12 행 정정. 중력 1스텝 지연은 규약 안. 크롤러 구는 있으나 접촉력 0이라 문제없음.
- Δt 2×10⁻⁴ s 조건 ①: V7 결과와 맞지만 $c_t$ 배율과 구분되지 않아 확인으로 보지 않는다. S3 V8(a) 그대로. 선택 사전 점검: V7 yaw 2 s를 Δt 2×10⁻⁴·5×10⁻⁵ s로 재실행(Δt 인자 필요).
- 고친 곳: S2a(위험 ②, 체크리스트). 0절 S2a 행의 "크롤러 없음"은 "크롤러 접촉 없음"으로 읽는다(체크리스트에 적음).

개정 8(2026-10-20, dynamics-expert 편집): **S1 최종 판정(통과)** 과 결정 사항을 반영했다(근거 `00_docs/01_dynamics/dynamics_model.md` 개정 11, 5.2절).
- **S1 통과(최종)**: V0~V3·V13·R16, 4사례(상단·중단·하단 해석 초기화, 상단 무초기화 53 s 교차). 선형 기준값과의 차(최대 67 N)는 P-δ 기하 비선형이다. 독립 6자유도 비선형 정역학(`04_scripts/01_dynamics/run_s1_pdelta_check.py` → `06_analysis/00_dynamics/s1_pdelta_check.json`)이 Chrono를 0.24 N 안에서 재현한다.
- **V0 재질 항목(사용자 결정 2026-10-20)**: Chrono가 float32로 저장하는 SMC 재질 값($k_n$, $g_n$, $k_t$, $g_t$, μ)은 "float32로 반올림한 YAML 값과 정확히 같음"으로 판정한다. 나머지 V0 항목은 상대차 ≤ 1×10⁻⁹ 그대로다. 정적 하중 영향 ≤ 0.04 N. `verify/s1.py`가 이미 이 방식이다.
- **해석 정적해 초기화 = 기본**(2절 규칙 1 확정). 낙하 초기화의 접선 예하중(±4~5 kN)은 S2a V12 수평력(±0.75~0.80 kN) 판정을 가리므로, V12는 부싱 변형 0 + 중력 램프로 시작한다.
- **S2b 구동기**: `ChLinkMotorLinearSpeed` → **`ChLinkMotorLinearPosition` + 훅에서 $s_{ref}$ 적분**(R16 스냅숏 때문). 단일 다리 Chrono 시험에서 동역학적으로 같다(1스텝 위상 $u\Delta t$, 힘 차 $k\,u\Delta t$ ≈ 48 N). 관성 스파이크 $m_{rod}\Delta v/\Delta t$ 주의(V11b).
- **R14 API 정정**: `SetFamilyMaskNoCollisionWithFamily` → `DisallowCollisionsWith` / `CollidesWith`(pychrono 10).
- **3.1절 모듈 표**에 S0·S1 산출 모듈을 반영했고, **6절 #24**의 P코어 고정은 `hostcpu.py`로 구현됐다고 표시했다.
- 고친 곳: 0절 S2b 행, R14, S1(만드는 것·V0 행·체크리스트), S2b(만드는 것·V0(크롤러) 행·위험·체크리스트), 3.1절 표·역할, 6절 #24.

개정 7(2026-10-20, dynamics-expert 편집): 사용자 결정 두 가지를 반영했다.
- **V4 판정 기준 시각 = 감쇠 3자유도 동적 접지 시각**(준정적 시각은 참고로 기록). 허용폭은 다리별 ±0.05 s 그대로. 동적 기준해: D FL 15.050 / FR 15.049 / RL 15.177 / RR 15.177 s, ×3 15.253 / 15.253 / 15.147 / 15.146 s, 강체 크롤러 극한(V4(NSC)) 15.382 / 15.382 / 15.040 / 15.040 s(`06_analysis/00_dynamics/reference.json`, `run_reference.py` `add_dynamic_touch`). 감쇠 가정(다리 ζ 0.03, 크롤러 0.05)과 적분기는 같은 키 아래 meta에 있다. 다리 ζ 0.01~0.10에서 ≤ 2.1 ms, 크롤러 ζ 0.02~0.3에서 ≤ 4.7 ms(롤러만 감도 포함) 움직인다. R12 경로: V4·V4(NSC)의 `… / quasi_static_events_s / touch_s (FL, FR, RL, RR)`를 `… / dynamic_events_s / touch_s (FL, FR, RL, RR)`로 바꿨고 감도 블록 `reference.json / lift_V4_compliant_crawler / dynamic_touch_damping_sensitivity`를 더했다. 준정적 키는 `reference.json`에 남아 있지만 백틱 경로에서는 뺐다(판정 기준이 아니므로).
- **일반 실행 Δt 1×10⁻⁴ s 유지, 2×10⁻⁴ s 완화는 조건부 검토**(`dynamics_model.md` 4.3절 개정 8 검토). V8(a) 판정을 모드별(1~6차 각각 ≤ 0.1 ζ, 1차는 상한만, 3차 $\zeta_{num}$ 예측 ±30 %, 2Δt/Δt 비는 3차)로 바꾸고, S2a V7 진단 ①~⑤에서 빼는 수치 감쇠를 $r_i\omega_i\Delta t/2$(1×10⁻⁴ s: 6.3×10⁻⁵ / 2.3×10⁻⁴, 3차 1.8×10⁻³)로 고쳤다. S3 체크리스트에 "V8(a) 통과 시 2×10⁻⁴ s 복귀를 사용자에게 다시 묻는다" 결정 대기 항목을 넣었다.
- 고친 곳: S2a V7 진단 행, S3 V8(a)·V4 행·위험 ①-2·체크리스트, S7 표 행·V4(NSC) 행·체크리스트, 6절 Δt 확정 행.
- 정리(2026-10-20, 무결성 점검, dynamics-expert): 머리말과 3.1절 표·3.4절 단위 시험 행을 실제 코드 상태(`engine.py`, `verify/reference.py`, 단위·Chrono 시험 파일)로 고쳤고, S2b 크롤러 정착 행의 "뒤 롤러열 0"을 "뒤 끝 슈 0, 맨 뒤 롤러열 9.59 kN"(`crawler_layout_check.json`)으로 바로잡았다. 절차·판정·기준값은 그대로다.
- 보완(2026-10-20, cad-expert): S0 마지막 항목 **전체 규모 스텝 비용 실측**을 반영했다(`06_analysis/01_chrono/step_cost_S0.json`). L1 패드 접지 0.190~0.195 ms/스텝(계획 단가 0.2 ms의 0.95~0.98배), 크롤러 정착 0.071~0.074 ms(0.35~0.37배), P코어 고정 기준. OS 기본 배치는 E코어로 가 2.5배 느려진다. 고친 곳: S0 체크리스트·단계 표 S0 행, 4절(계획 단가 표, 실측 절, 1×10⁻⁵ s 표 V9 V4 행), 6절 #24, 7절 스텝 단가. 단계별 합계·벽시계 값은 바꾸지 않았다.

개정 6(2026-10-20, dynamics-expert 편집): [dynamics_model.md](../01_dynamics/dynamics_model.md) **개정 8**(크롤러 접촉 **D안** 사용자 결정, CLAUDE.md "크롤러 접촉 배치")을 반영했다. 절차는 그대로이고 크롤러 구간 수치와 V4 판정 문구만 바뀌었다.
- **V4 판정**: "첫 접지 = 후방 쌍 15.006 s" → **다리별 접지 시각이 같은 배치 기준해와 각각 ±0.05 s**. L1 D 기준해 FL 15.051 / FR 15.049 / RL 15.148 / RR 15.148 s(×3 감도 실행이면 15.243 / 15.243 / 15.147 / 15.146 s). L2b-NSC(강체 크롤러 극한) 15.375 / 15.375 / 15.040 / 15.040 s. 접지 순서는 판정하지 않는다(크롤러 강성 가정에 따라 뒤집힘).
- 크롤러 위 정착: ≥ 23.2 → **≥ 65.5 s**(`simulation.settle_on_crawler_min_s` 65.47, 크롤러 위 pitch 1.327 Hz·ζ 0.0084). 크롤러 정착 자세(해석해)로 초기화하면 필요 없다.
- 기준값 경로 표기(R12 파서가 읽는 백틱 표기는 새 키만 둔다): 크롤러 모드 키를 옛 "crawler_on_floor_modes (default layout, legs at 0)"에서 "crawler_on_floor_modes (layout D, legs at 0)"로 바꿨다. V4·V4(NSC)에 다리별 접지 경로를 더했고, V4(NSC)의 옛 기준 "operating_point / time_to_touch_s(후방 값)"를 강체 극한 배치 경로로 바꿨다. 옛 배치 키 "default 2x9 (YAML contact.crawler.sphere_layout)"는 `reference.json`에서 없어졌다.
- 고친 곳: 2절 초기 조건 규칙 2, S0 비용 체크리스트, S2b(크롤러 정착 행·위험 ①·체크리스트), S3(lift 절차, V4, 체크리스트), S7(V4(NSC), 체크리스트), 0·4절 비용(S2b, S7), 5절 크롤러 키 행, 6절 #8·#10, 7절 정착 길이·크롤러 형상. 개정 5 이하 기록의 옛 값은 이력으로 둔다.

개정 5(2026-10-20): [dynamics_model.md](../01_dynamics/dynamics_model.md) **개정 7**(감쇠비 사용자 결정, 근거 [damping_survey.md](../01_dynamics/damping_survey.md))과 용도별 시간 간격 결정(CLAUDE.md "시뮬레이션 시간 간격")의 **수치만** 반영했다. 절차·판정 구조는 그대로다.
- 감쇠: 1차 로킹 ζ 0.0129 → **0.00777**, τ₁ 6.9 → **11.5 s**. 크롤러 위 heave ζ 0.10 → 0.05(콘크리트), 크롤러 위 최대 τ 2.52 → **5.05 s**. 감쇠 ζ(Q6)는 결정됨(5절).
- 정착 길이: 크롤러 위 ≥ 11.6 → **≥ 23.2 s**(`simulation.settle_on_crawler_min_s` 23.24; 개정 6 D안에서 **≥ 65.5 s**, 65.47), 패드 위 ≥ 32 → **≥ 53 s**(`simulation.settle_on_pads_min_s` 52.86).
- 시간 간격: 일반 실행 L1·L2b-NSC 2×10⁻⁴ → **1×10⁻⁴ s**(로킹 수치 감쇠 규칙 상한 L1 1.386×10⁻⁴ s), 기준해·접지 전환 해석 **1×10⁻⁵ s**(`simulation.dt_reference_s`, `simulation.dt_transition_s`).
- V4 잔류 판정 시점: 마지막 정지 뒤 10 s → **15 s**(10 s 뒤 선형 예측 pitch 1.3×10⁻³°가 0.001°를 넘음).
- 4절 비용을 dt 1×10⁻⁴ s(스텝 2배), V4 정착 15 s, 정착 길이, 1×10⁻⁵ s 전환 창·기준해로 다시 계산했다. 측정 근거 표(Δt 2×10⁻⁴ s)는 측정 당시 값으로 둔다.
- 고친 곳: 2절 초기 조건 규칙, R7, S1 위험·체크리스트, S2a V7 진단(판단 대기 표시), S2b 크롤러 정착, S3 lift 절차·V8(a)·V4·V9, S6 runner 스텝 수, S7 위험 ②, S8 위험 ②, 0·4절 비용, 5절 Δt·감쇠 행, 6절 #7·#8, 7절 정착 길이·$n_{lift}$. 개정 1·2 기록의 옛 값은 이력으로 두고 새 값만 덧붙였다.
- 판단 대기 해소(2026-10-20): S2a V7 진단 문구를 dyn 계산(`06_analysis/00_dynamics/v7_diagnostic.json`, `dynamics_model.md` 개정 7 보완)으로 바꿨다. $c_t$ 2배는 1·2차 ζ를 +16 % / +34 %만 올려 1·2차만으로는 확정하지 못하므로, 의심되면 yaw 초기 속도 2 s로 3차(yaw-sway, 접선 몫 99.4 %) ζ를 재서 확정한다. V12 정착은 ≥ 53 s로 늘렸고(사용자 결정), 부상 판정 $n_{lift}$는 시간 기준 1 ms로 정했다(사용자 결정).

개정 4(2026-10-20): S0 파라미터 로더 `03_src/outrigger_sim/params.py` 구현(python-expert, 단위 시험 47건 통과)을 반영했다.
- 지문 두 가지를 구분했다: `Params.sha256`(오거 level 포함, `meta.generated` 제외, 오버라이드 반영)은 스냅숏 복원 판정과 실행 meta에, `Params.file_sha256`(원본 파일 바이트)은 파일 동일성 기록에 쓴다(R16, S3 meta).
- 오버라이드는 파생값을 다시 계산하지 않는다. β 감도(S4)는 β에서 파생된 강성 키를 직접 오버라이드한다.
- 모델 선택(L1/L2b)은 S0에서 빼고 S7로 미뤘다. S0 입력 키가 L1뿐이고 L2b_NSC 블록은 키 구성이 달라서다.
- 고친 곳: R16, S0 체크리스트, S3 체크리스트(meta), S4 만드는 것, S7 만드는 것, 3.1절 모듈 표·역할, 3.4절 단위 시험 표.

개정 3(2026-10-20): 사용자 결정(CLAUDE.md 2026-10-20 기록)을 반영했다. 근거는 [imu_cabin_and_accuracy_review.md](../05_sensors/imu_cabin_and_accuracy_review.md) 5.2절 표(개정 2 기준 513·338·559행 지적)와 [control_candidates_comparison.md](../04_control/control_candidates_comparison.md) 7.3절이다.
- 자세 정확도 목표를 ±0.1°에서 **±0.2°**로 바꿨다. 완료 판정 데드밴드 0.03°는 유지한다. IMU 현장 영점 교정은 운용 절차로 의무다. 센서 정지 영점 오차 허용은 0.13°(2.27 mg)다(캐빈 장착 몫 0.03° 포함 예산).
- IMU 장착점: **캐빈 바닥 아래 상부 프레임**, 기체 좌표 (0.31, 0.88, 0.040) m(C1, 2026-10-20 사용자 결정; 이전 가정 (0.20, 0.88, 0.30) m). 로킹 순간 회전 중심이 지면 아래라 높게 달수록 겉보기 기울기 증폭이 커진다.
- 자세 신호 필터: 2차 저역통과(1차 τ 0.5 s × 2단).
- 제어 구조: C2 잠정 확정, 대안 C8. 접지 판정은 물리 기반 결합 판정(압력·스트로크·자세) + 탐침이고 ML/DL은 비교 후보다.
- 고친 곳: S6(만드는 것, 제어기 검증 항목 표 신설, 위험 ②, 체크리스트), 3.5절 제어기 트랙, 5절 결정 상태.

개정 2(2026-10-20): [dynamics_model.md](../01_dynamics/dynamics_model.md) 개정 5(기존 기준값 변경 없음, 새 키만)를 반영해 "개정 5 기준" 자리를 실제 내용으로 채웠다.
- V4: 크롤러 위 정착 ≥ 11.6 s(개정 5에서 ≥ 23.2 s), t = 0 모터 출발(다리 0 m), 다리별 $e_{op}$ 계단 정지, 첫 접지 = 후방 쌍. 기준은 `reference.json / lift_V4_compliant_crawler`다. 개정 1의 "접지 − 10 mm 출발" 안은 지웠다.
- V7: 모드 투영 $\eta=\Phi^TMq$(`mode_shapes_rev5`)를 기본으로 하고 ERA/SSI는 대안으로 둔다.
- V14는 시험 다리를 RL+로 바꾼다(`V14_rev5`). V15는 (a) 단방향 상승, (b) 0 → 10 → 0 mm 왕복으로 나눈다(`V15_rev5`).
- 크롤러 규약은 YAML 새 키 이름(`contact.crawler.*`, `simulation.settle_on_*`)으로 참조한다. R8 크롤러 적용은 개정 5에서 확인됐다.
- V8(a) 배치, V9 매끄러운 시험, V11b 스텝별 판정, 정착 32 s(개정 5에서 53 s), β 감도 감쇠 고정이 개정 5 문구와 같은지 확인했다(차이는 V9 ② 창 5 s, 최종 자세 비교 3주기 평균, β 감도에서 $g_n$·부싱 $k_t$도 고정 — 반영함).
- 실행 시간을 다시 계산했다(4절).

개정 1(2026-10-20): dynamics-expert 검토 [chrono_build_plan_review.md](chrono_build_plan_review.md)(판정 "수정 후 진행", 19건) 가운데 cad-expert 몫을 반영했다.
- 초기 조건: 해석 정적해로 시작한다. 안 되면 정착 ≥ 32 s(개정 5에서 ≥ 53 s). 정착 상태는 저장해 재사용한다(#2).
- 지면 부싱을 S1부터 t = 0에 만든다(#15). S2를 S2a(부싱·V7 진단·V12)와 S2b(모터·크롤러·접지 이벤트)로 나눴다(#7).
- V4: 크롤러 위 정착 구간을 넣었다. 접지 시각은 정착 자세 기준으로 첫 접지 다리만 판정한다. 모터는 계단으로 세운다(#1, #13, #19).
- 수치 감쇠·수렴:
  - V8(a)를 S3의 V9 앞으로 옮겼다. 60 s 창으로 Δt·2Δt 비례를 확인한다(#3).
  - V9 차수는 매끄러운 시험에서만 잰다(#11).
- V7: 초기 속도 가진과 6채널 다출력 식별로 바꿨다(#6). V12 초기 조건과 중력 램프를 정했다(#8).
- 접촉·구동기 규약:
  - 부싱 복귀 사상에 $\max(N,0)$과 부상·재접지 히스테리시스를 넣었다(#10).
  - V11b는 물리 스텝마다 판정하고, 단일 다리는 양방향 스프링으로 묶는다(#12).
  - V11은 상부체를 고정한 공중 다리로 한다(#17).
- β 감도: 감쇠 고정, 정적값과 비감쇠 진동수만 본다(#14).
- 크롤러 아래 바닥 패치와 크롤러 재질 규약을 정했다(#9 cad 몫). 충돌 패밀리 필터를 넣었다(#18).
- L2b-NSC 진동수는 배열 앞 6개만 쓴다. 기준값 키는 전체 문자열로만 적는다(#16).
- V4·V14·V15 기준값과 크롤러 감쇠는 dynamics-expert가 [dynamics_model.md](../01_dynamics/dynamics_model.md) **개정 5**에서 다시 정한다(#1, #4, #5, #9). → 개정 2에서 실제 내용으로 채웠다.
- 3절을 실제 뼈대(`pyproject.toml`, 하위 패키지 5개, `05_tests/conftest.py`)에 맞췄다. 4절 실행 시간을 다시 계산했다.

공통 사항:
- 입력(읽기만 함): `CLAUDE.md`, `README.md`, `02_params/rexome33.yaml`, `00_docs/01_dynamics/dynamics_model.md`(개정 7), `00_docs/01_dynamics/damping_survey.md`, `00_docs/01_dynamics/actuator_L2_feasibility.md`, `06_analysis/00_dynamics/actuator_L2_feasibility.json`, `00_docs/03_chrono/chrono_stick_friction_test.md`, `04_scripts/02_chrono/test_stick_friction.py`, `00_docs/02_hydraulic/hydraulic_circuit.md`, `06_analysis/00_dynamics/reference.json`, `06_analysis/01_chrono/stick_friction.json`, `00_docs/03_chrono/chrono_build_plan_review.md`, `00_docs/05_sensors/imu_cabin_and_accuracy_review.md`(개정 3), `00_docs/04_control/control_candidates_comparison.md`(개정 3).
- 판정 기준은 `00_docs/01_dynamics/dynamics_model.md` 5절 V0~V17이다. 이 문서는 기준을 새로 만들지 않고 단계에 배치한다.
- 담당(CLAUDE.md 작업 규칙):
  - **cad**(cad-expert): Chrono 모델·시뮬레이션 스크립트
  - **dyn**(dynamics-expert): V 판정
  - **py**(python-expert): 제어기·IMU 모델·데이터 처리
- 작업량: 소 = 에이전트 호출 1회, 중 = 2~3회, 대 = 4회 이상.

## 0. 요약

| 단계 | 목표 | 모델 | 통과 기준(V) | 담당 | 작업량 | 시뮬레이션 길이 / 예상 벽시계(직렬, 4병렬) |
|---|---|---|---|---|---|---|
| **S0** | 공통 기반: 로더·타입·규약 단위 시험, 부싱 회귀(히스테리시스 포함), 정착 상태 저장, 비용 측정 | — | V0(규약 부분), 블록 회귀 | cad (+py: 타입 검토) | 중 | 약 30 s + 비용 측정 8 s / 약 1.5분 |
| **S1** | 상부체 + 고정 다리(운용 신장) + 지면 부싱(t = 0)으로 수평 정적, 정착 상태 저장 | L1 | V0, V1, V2, V3, V13 | cad → dyn | 중 | 103~174 s / 3.5~6분 |
| **S2a** | 지면 부싱 동특성 진단과 경사 정적 | L1(모터·크롤러 없음) | V7 진단(1·2차), V12, V13 | cad → dyn | 중 | 약 217 s / 7분 |
| **S2b** | 구동기(위치 모터 + 훅 $s_{ref}$ 적분, 개정 8), 크롤러 접촉(D안 구 24개: 롤러 2×6 + 틈 있는 끝 슈 2×6), 접지 이벤트 부싱 생성·소멸, 크롤러 위 정착 상태 저장 | L1 | V0(모터 부호, 크롤러 배열·재질·충돌 필터), V11(공중 다리), V13, 이벤트 단위 시험 | cad → dyn | 중 | 약 281 s / 9.5분(크롤러 정착 해석해 초기화면 약 84 s / 3분) |
| **S3** | 수치 감쇠 확인 → 들어 올림(모터 출발 → 계단 정지) → 다리 단독 신장, Δt 확정 | L1 | V8(a), V4, V5, V6, V9 | cad → dyn | 대 | 약 1,407 s / 47분, 약 12~13분(V4 기준해 1건 약 11분이 병목) |
| **S4** | 6개 모드(모드 투영), 에너지 수지, β 감도 | L1 | V7(6모드), V8(b), β 감도 | cad → dyn | 중 | 약 531 s / 18분, 약 5분 |
| **S5** | 오거 3단계 | L1 | V10, V0(오거 합성) | cad → dyn | 소 | 약 165 s / 5.5분 |
| **S6** | 센서 진값, 210 bar 힘 포화(물리 스텝마다), 제어기 경계 | L1 | V11b, V17 기록 경로 | cad + py → dyn | 중 | 약 115 s / 4분 |
| **S7** | L2b-NSC | L2b-NSC | V0~V13(L2b-NSC 열, V4 다리별 동적 15.382 / 15.382 / 15.040 / 15.040 s), V14(RL+) | cad → dyn | 대 | 약 3,001 s / 30~60분, 7.5~15분 |
| **S8** | 실 마찰, 카운터 밸런스, D2 외란 | L2b-NSC(+L1 V17) | V15(a)(b), V17, V8(b) | cad → dyn | 대 | 약 2,820 s / 33.5~59.5분, 8.5~15분 |
| **S9** | SCM(파라미터 확보 후) | L2b-NSC + SCM | V16 | cad → dyn | 대 | 미측정 |

제어기 트랙(py)은 다음 순서로 끼어든다(3.5절): S3 뒤 개루프 재생, S6 뒤 L1 폐루프, S7·S8 뒤 L2b-NSC 재판정.

## 1. 모든 단계에 걸리는 규약 (체크리스트)

S0에서 단위 시험으로 만들고, 이후 모든 단계가 이 시험을 통과한 코드를 쓴다.

| # | 규약 | 근거 | 확인 방법 |
|---|---|---|---|
| R1 | 중력을 항상 명시한다: `SetGravitationalAcceleration((0,0,-9.80665))`. pychrono 10의 기본값은 0벡터다. 중력 램프(V12)도 이 함수로만 바꾼다 | `dynamics_model.md` 1.1 | V0. `make_system()` 한 곳 |
| R2 | 충돌 시스템을 지정한다: `SetCollisionSystemType(Type_BULLET)` | CLAUDE.md | V0 |
| R3 | Z-up, 기체 좌표(x 전방, y 좌측). YAML이 이미 CAD→기체 회전을 적용했으므로 코드에서 다시 돌리지 않는다 | YAML `meta.frame` | V0 |
| R4 | `ChLinkMotorLinear*`는 링크 프레임 **Z축**을 구동한다. 링크 Z를 기체 −z로 둔다. 모터 반력 부호도 확인한다 | `dynamics_model.md` 2.1 | V0 단위 시험 |
| R5 | SMC Hooke `gn`은 유효 질량당 값이다. 패드는 $g_n=c_n/m_{moving}$(YAML `contact.rigid_floor.L1.gn_per_pad_1_s`). 크롤러는 R13을 따른다 | 블록 시험 2.2 | V0, V7 감쇠 |
| R6 | 고정 바닥 바디 질량 1×10⁹ kg과 `SetFixed(True)`를 함께 둔다 | YAML `contact.rigid_floor.ground_body_mass_kg` | V0 |
| R7 | 부싱 감쇠는 입력의 2배로 작용한다. 입력 = $c_t/2$ | 블록 시험 2.3 | V0(부싱 입력 = $c_t/2$ 되읽기가 가장 직접적인 방어). V7에서 접선 모드(3~6차) ζ가 기준값의 약 2배(0.07~0.10)면 위반(`dynamics_model.md` 개정 7 V7 진단). S2a에서는 1·2차(+16 % / +34 %)로 의심하고 3차 ζ(×1.99)로 확정한다 |
| R8 | 모든 SMC 재질(패드 구, 크롤러 구, 바닥 패치)은 $k_t=g_t=\mu=0$이다. 접선은 지면 부싱(L1) 또는 NSC(L2b)가 맡는다. `ChLoadBodyBodyBushingPlastic`은 쓰지 않는다. 크롤러 μ(YAML `contact.crawler.friction` 0.5)는 L1에서 쓰지 않고, L2b-NSC 크롤러 접촉에만 쓴다 | `dynamics_model.md` 4.1·4.2. 크롤러 적용은 **개정 5에서 확인됨**(4.2절 크롤러 행, 10절 `contact.crawler.smc_material`) | V0. 크롤러 접지 구간의 수평 표류는 판정하지 않고 기록만 한다 |
| R9 | `GetPos()` 등은 참조를 돌려준다. `probes.py`에서만 읽고 즉시 복사한다 | 블록 시험 4절 | 단위 시험 |
| R10 | 쿼터니언은 wxyz다(scipy xyzw와 섞지 않는다). 자세는 ZYX 내재 오일러각으로 쓴다 | `dynamics_model.md` 1.1 | `frames` 단위 시험 |
| R11 | 적분기는 `EULER_IMPLICIT_LINEARIZED`다. 솔버는 L1 **`SPARSE_LU` + 희소 패턴 고정(`LockSparsityPattern(True)`)**(사용자 결정 2026-10-20, 근거 4절 선형 솔버 벤치마크: 전체 규모 L1 잠금 켬 QR 147 / LU 133 / Pardiso 447 µs/스텝, 결과 동일). 옵션은 `SPARSE_QR`·`PARDISO_MKL`과 잠금 끔(`make_system(solver=..., lock_sparsity_pattern=False)`). Pardiso는 env 미활성 실행에서 `libomp.dll`을 미리 로드해야 한다(S0 체크리스트 메모). 잠금 상태에서 시스템을 통해 항목을 넣고 빼면(R15 부싱 생성·소멸) Chrono가 패턴을 다시 분석한다. 시스템이 모르는 구조 변경(이미 들어간 `ChLoadContainer`에 하중 추가, `SetFixed` 전환 등) 뒤에는 `force_sparsity_pattern_update()`를 부른다. L2b-NSC는 `PSOR` 50회. `SetContactStiff` 같은 실행 설정은 V8(a)와 본 실행에서 같게 둔다 | `dynamics_model.md` 4.2·4.3, 검토 #3 | V8(a), V9, V13 |
| R12 | 기준값은 런타임에 `reference.json`(과 개정 5 이후 문서가 지정하는 파일)에서 읽는다. **키는 전체 문자열 상수로만 쓰고**(괄호·공백 포함) 키 존재 시험으로 막는다 | CLAUDE.md, 검토 #16 | `verify/reference.py` 시험 |
| R13 | 크롤러 접촉 **D안**(사용자 결정 2026-10-20, `dynamics_model.md` 3.8절; 이전 2×9 bbox 균등 배열은 폐기): 트랙 2개(y = ±`contact.crawler.sphere_layout.track_centre_y_m`) × (롤러 위치 구 6개 + 틈 있는 끝 슈 구 6개(앞뒤 끝마다 3개)) = **구 24개**, `sphere_layout.scheme` = `rollers_plus_gapped_end_shoes`. 롤러 구는 `.roller_x_m`, 구 바닥 = `ground.crawler_bottom_z_m`. 끝 슈 구는 `.end_shoe_x_m`, 구 바닥 = 바닥 + `.end_shoe_gap_m`(같은 순서, 2~22 mm)이다. 끝 슈 구는 **단방향**이라 틈이 닫힌 뒤에만 접촉한다(Chrono에서는 구를 틈만큼 위에 두면 된다). 반지름 `.sphere_radius_m`. 재질은 24구 모두 같다: `contact.crawler.kn_per_sphere_N_m`(= `kn_total_N_m` / 롤러 12구, 바닥 접촉 합 = kn_total), `contact.crawler.gn_per_sphere_1_s`(= `damping_total_N_s_m` / 12 / 상부체 바디 질량. 크롤러 구가 상부체 바디에 붙어 있으므로 $m_{eff}$ = 상부체 질량), $k_t=g_t=\mu=0$(`contact.crawler.smc_material`). 감쇠 근거 키는 `contact.crawler.damping_ratio_heave`, `contact.crawler.damping_total_N_s_m`이다. 강성 감도는 `contact.crawler.kn_total_sensitivity_range_N_m`(×1, ×3; ×3이면 `kn_per_sphere`와 대시포트를 같은 heave ζ로 함께 바꾼다). 크롤러 밑에 **패드 패치와 별도인 바닥 패치**를 두고 크롤러 구와 같은 재질 값을 준다. 위치·틈은 CAD B-rep 캐시(`01_cad/06_brep/derived/crawler/`, 다른 기종 REXOME25 하부체 — 가정)에서 `export_params.py`가 읽는다. 값은 이 문서에 복사하지 않는다 | 검토 #9, `dynamics_model.md` 개정 5 4.2·10절, 3.8절(D안) | V0(구 24개 위치·틈·재질), S2b 크롤러 정착 |
| R14 | 충돌 패밀리: 바닥, 상부체(크롤러 구 포함), 로드 구를 서로 다른 패밀리로 둔다. 로드–상부체 쌍과 로드–크롤러 쌍을 끈다(`contact.crawler.collision_filter`). 크롤러 구는 상부체 패밀리라 한 번에 꺼진다. API는 `GetCollisionModel().SetFamily(k)` / `DisallowCollisionsWith(k)` / `CollidesWith(k)`(pychrono 10, S1에서 확인. 옛 이름 `SetFamilyMaskNoCollisionWithFamily`는 없다; `chrono/contact.py` `set_family`) | 검토 #18, 개정 5 V0 추가 | V0, V13 "다리당 접촉점 1" |
| R15 | 지면 부싱 복귀 사상은 $N\leftarrow\max(N,0)$으로 한다. 부상은 "$N\le0$이 $t_{lift}$ = 1 ms 연속"일 때($n_{lift}=\lceil t_{lift}/\Delta t\rceil$스텝, **시간 기준**, 사용자 결정 2026-10-20), 재접지는 "$N>N_{th}$"일 때 판정한다(히스테리시스). 부싱 생성·소멸 횟수와 시각을 기록한다. $n_{lift}$와 $N_{th}$는 가정(7절)이고 **S2b 이벤트 시험에서 조정**한다(chatter 0, Δt 1×10⁻⁴·1×10⁻⁵ s 사건 시각 차 ≤ 1 ms일 때 유지). **훅 입력 1스텝 지연 규약**(dynamics-expert 판정 2026-10-20, `dynamics_model.md` 4.6절): 훅에서 바꾼 부싱 고정점·감쇠·외력·모터 입력이 다음 스텝 Update에서 읽히는 1스텝(Δt) 지연을 모델 규약으로 둔다(즉시 반영 강제 안 함, S0 회귀 유지). 영향은 미끄럼 마찰 초과 $k_tv\Delta t$와 사건 시각 +Δt뿐이다. 기록 meta에 `input_lag_steps: 1` | 검토 #10 | S2b 이벤트 시험, V6, V8(b) |
| R16 | 정착 상태 저장·재사용: `snapshot()`이 바디 위치·자세·속도, 모터 위치, $s_{ref}$, 부싱 고정점·상태, 시스템 시각, 사용한 파라미터 지문 `Params.sha256`(오거 level 포함, `meta.generated` 제외, 오버라이드 반영)을 담는다. `restore()`는 같은 `Params.sha256`일 때만 허용한다 | 검토 #2 | S0 왕복 시험(저장 → 복원 → 1 s 진행이 이어 돌린 결과와 같음) |

## 2. 단계별 계획

기준값 키 표기: 파일 이름 뒤에 JSON 경로를 ` / `로 이어 **전체 문자열**로 적는다. `<level>`은 `top`, `middle`, `bottom` 중 하나다. 예: `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / contact_force_N`.

초기 조건 규칙(검토 #2, 모든 정적 판정에 적용):
1. **해석 정적해로 시작**한다. 상부체 위치·자세는 V2 침투·V3 자세 기준값(`reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / static_penetration_or_compression_mm`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / static_attitude_deg (roll, pitch)`)에서 구한다. L2b-NSC는 같은 하위 키를 `L2b_NSC_force_motor_axial_spring_lateral_bushing` 아래에서 읽는다. 부싱은 t = 0에 접선력 0으로 만든다. 그 뒤 10 s 정착 + 판정 창.
2. 패드 위 상태를 해석 정적해로 시작할 수 없으면 정착을 **≥ 53 s**(`simulation.settle_on_pads_min_s` 52.86)로 둔다. 근거: 1차 로킹 ζ 0.00777, 1.785 Hz에서 $\tau=1/(\zeta\omega)$ = 11.5 s이고, 1/100 감쇠에 $\tau\ln100$ ≈ 53 s가 든다. 크롤러 위 정착(다리 0 m)은 **≥ 65.5 s**(`simulation.settle_on_crawler_min_s` 65.47, D안 크롤러 위 최대 τ 14.2 s × ln 100, 크롤러 ζ 0.05; 개정 5까지 2×9는 23.2 s)다. **크롤러 정착 자세(해석해, `reference.json / lift_V4_compliant_crawler / layouts / D rollers + gapped end shoes (YAML contact.crawler.sphere_layout)` 하위 `settled_on_crawler (legs at 0)`)로 초기화하면 이 정착은 필요 없다.** 초기화하지 못할 때만 이 시간을 둔다(`dynamics_model.md` 개정 8 4.5절 1).
3. 정착 결과는 R16 스냅숏으로 `07_results/states/`에 저장한다. 뒤 단계 시나리오는 이 상태에서 시작한다.

### S0 공통 기반

- **목표**: 같은 규약·파라미터·기록 형식을 쓰게 한다. 블록 시험 구현을 라이브러리로 옮겨 결과가 같은지 확인한다. 정착 상태 저장을 만든다. 전체 규모 스텝 비용을 잰다.
- **만드는 것**(3.1절의 "계획" 모듈):
  - `params`, `frames`, `signals`(옛 이름 `types`), `engine`, `record`
  - `chrono/system.make_system(model)`
  - `chrono/ground_bushing.GroundBushingCoulomb`: 블록 시험 `hook()`을 이식하고 4다리, R15를 넣는다
  - `verify/reference`
  - 스냅숏(R16)
- **입력 키**:
  - `meta`: `gravity_m_s2`, `leg_order`, `frame`
  - `contact.rigid_floor`: `friction`, `ground_body_mass_kg`, `damping_input_convention`
  - `contact.rigid_floor.L1`: `kn_per_pad_N_m`, `kt_per_pad_N_m`, `cn_per_pad_N_s_m`, `ct_per_pad_N_s_m`, `gn_per_pad_1_s`, `bushing_stiffness_per_pad_N_m`, `bushing_damping_input_per_pad_N_s_m`, `slip_damping_reenable_speed_m_s`
  - `simulation.L1.dt_s`
- **통과 기준**

| 항목 | 기준값 | 허용 | 출처 |
|---|---|---|---|
| 파라미터 로더 | YAML 원문과 같은 값, 문자열로 읽힌 수치 0건 | 같은 float | `02_params/rexome33.yaml` |
| 부싱 회귀 2° 10 s | 미끄럼 0, 탄성 변위 | 미끄럼 < 1×10⁻³ mm, 탄성 ±0.1 % | `stick_friction.json / cases / name = "Bushing 2deg"` |
| 부싱 회귀 수평 v0 | 진동수, ζ | ±0.1 %, ±2 % | `stick_friction.json / cases / name = "Bushing flat v0"` |
| 부싱 회귀 30° 2 s | 미끄럼 거리 | ±0.5 % | `stick_friction.json / cases / name = "Bushing 30deg (tan>mu, must slide)"` |
| 히스테리시스(R15) | 단일 블록을 들었다 놓기: 생성 1, 소멸 1, chatter 0 | 횟수 일치 | 이 계획 |
| 스냅숏 왕복(R16) | 저장 → 복원 → 1 s 진행 결과가 이어 돌린 결과와 같음 | 위치 차 ≤ 1×10⁻¹² m | 이 계획 |
| V0(규약 부분) | R1·R2·R6 | 일치 | 1절 |

- **의존**: 없음.
- **위험**: PyYAML 부동소수 표기 함정이 있다. 로더가 수치를 `float`로 강제하고 실패하면 예외를 낸다. 블록 시험 스크립트는 회귀 기준으로 그대로 둔다.
- **담당·작업량**: cad 중. 타입(`signals`)은 py가 검토한다.
- **체크리스트**
  - [x] 패키지 뼈대, `pyproject.toml`(pytest·ruff 설정, 마커 `chrono`·`sim`·`slow`), `05_tests/conftest.py` (2026-10-20, 사용자 승인으로 생성됨)
  - [x] `params` + 전 키 왕복 시험 (2026-10-20, `03_src/outrigger_sim/params.py`, `05_tests/unit/test_params.py` 47건 통과)
  - [x] `frames`(wxyz 쿼터니언, ZYX roll·pitch, 기체↔CAD 변환, 원점 오프셋 `BODY_ORIGIN_IN_CAD_MM` 한 곳; R10) + 단위 시험 (2026-10-20, `05_tests/unit/test_frames.py`)
  - [x] `signals`(Command, Measurements, TruthState, Record 스키마) + 단위 시험 (2026-10-20, `05_tests/unit/test_signals.py`; 표준 라이브러리 `types`와 이름이 겹쳐 `types`에서 바꿈, 사용자 결정)
  - [x] `make_system()`(R1·R2·R11) (2026-10-20, `03_src/outrigger_sim/chrono/system.py`, `05_tests/chrono/test_system.py` 통과; R6 바닥 1×10⁹ kg·fixed, dt 용도별 YAML 선택, SMC·NSC 낙하 연기 시험 포함. Pardiso MKL 크래시(0xC06D007F)는 env 미활성 실행에서 llvm-openmp 포워더 `libiomp5md.dll` → `libomp.dll`을 찾지 못한 DLL 검색 경로 문제였고, Pardiso를 요청할 때만 `<env>\Library\bin\libomp.dll`을 절대 경로로 미리 로드해 해결했다(PATH 변경 없음). 낙하 시험에서 PARDISO_MKL·SPARSE_LU가 SPARSE_QR와 비트 단위로 일치. 시험 42건). **R11 기본 솔버 변경 반영(2026-10-20, 사용자 결정)**: L1 기본을 `SPARSE_LU` + 희소 패턴 고정으로 바꿨다(`L1_DEFAULT_SOLVER`, `L1_DEFAULT_LOCK_SPARSITY_PATTERN`, 인자 `lock_sparsity_pattern`, meta `solver.lock_sparsity_pattern`, 헬퍼 `force_sparsity_pattern_update()`). 기본 경로 낙하 시험은 이전 기준(QR, 잠금 끔)과 비트 단위로 같고, 실행 중 링크·부싱(새 컨테이너, 기존 컨테이너)을 넣고 빼도 잠금 켬 = 잠금 끔(차 0 m). 시험 53건
  - 잠금과 구조 변경(pychrono 10.0.0 확인): 잠금은 첫 Setup(또는 `ForceSparsityPatternUpdate()` 요청) 뒤 패턴 학습을 건너뛴다. 시스템을 통한 추가·제거는 `ChSystem::is_updated`를 지워 다음 스텝 Setup이 `analyze = true`로 불리고 패턴을 다시 만든다(그 스텝 행렬 조립 시간이 첫 스텝과 같음). 시스템이 모르는 변경(기존 컨테이너에 하중 추가, `SetFixed` 전환)도 Chrono가 원소를 삽입식으로 써서 결과가 같았다. 탐침 7사례(LU·Pardiso, 잠금 켬/끔/갱신) 모두 비트 단위 일치. 다만 `ForceSparsityPatternUpdate()`가 Chrono 문서의 처방이므로 그런 변경 뒤에는 헬퍼를 부른다. 처음부터 비활성인 링크를 `SetDisabled(False)`로 켜는 방식은 잠금과 무관하게 LU 분해 실패·QR/Pardiso NaN이 나서 이벤트 수단으로 쓰지 않는다(생성·제거로 한다)
  - [x] `engine`(SimEngine 프로토콜) (2026-10-20, `03_src/outrigger_sim/engine.py`, `05_tests/unit/test_engine.py` 25건 통과; `typing.Protocol` + `runtime_checkable`, `reset(start: AnalyticStart | Snapshot) -> TruthState`(시각 0, 명령 0), `restore`는 시각·유지 명령까지 그대로 이어감, `Snapshot`(엔진 이름·버전·모델, `params_sha256`, 시각, 유지 명령, 수치 배열 payload), 이름·모델·지문 불일치 시 `SnapshotMismatchError`, 수명 오류 `EngineNotReadyError`·`EngineClosedError`, `with`는 `contextlib.closing`. 오거 level은 `Params`(지문 포함)에 묶여 reset 인자가 아님)
  - [x] Chrono 10 SMC 감쇠 처리 확인: Hooke `gn = eff_mass × gn` 규약을 단일 접촉 감쇠 시험으로 확인(감쇠비 결정 반영 전제, `00_docs/01_dynamics/damping_survey.md`) (2026-10-20, `05_tests/chrono/test_smc_damping.py` 22건 통과, 진단 `04_scripts/02_chrono/smc_damping_check.py` → `06_analysis/01_chrono/smc_damping.json`; 소스 해석과 같음: c = gn·m₁m₂/(m₁+m₂)(바닥 1e9/1e3/1 kg), 재질 합성은 kn·gn 산술 평균, YAML gn으로 4패드 강체 heave ζ 0.02999/0.02998(Δt 1e-4/1e-5 s, 설계 0.03)·7.3938 Hz(설계 7.3933). SMC 접촉력은 명시 적분이라 ωΔt/2 수치 감쇠가 없고 `SetContactStiff(True)`는 효과 없음)
  - [x] `GroundBushingCoulomb`(R15 포함), 블록 회귀 3건과 히스테리시스 시험 (2026-10-20, `03_src/outrigger_sim/chrono/ground_bushing.py`, `05_tests/chrono/test_ground_bushing.py` 18건 통과; 블록 회귀는 기준 파일 값(`stick_friction.json` `reference`)·Δt 2×10⁻⁴ s·기본 SPARSE_LU+잠금으로 2° 탄성 변위 상대차 1.8×10⁻¹⁴·미끄럼 0, 수평 v0 4.702273 Hz·ζ 0.053112(기준과 2×10⁻¹⁰ 이내), 30° 미끄럼 상대차 −7×10⁻¹⁰. 들었다 놓기: Δt 1×10⁻⁴·1×10⁻⁵ s 모두 소멸 1·생성 1·chatter 0, 소멸 = 첫 N≤0 스텝 + (n_lift−1)Δt(n_lift 10/100), 재생성 고정점 = 착지점, 잠금 켬/끔 궤적 차 ≤ 1×10⁻¹² m. t = 0 `attach()`는 초기 조건이라 이벤트로 세지 않음. Chrono 스냅숏 함수(R16 Chrono 쪽)는 `chrono/snapshot.py`, `05_tests/chrono/test_snapshot.py` 19건)
  - [x] `record`(npz + meta.json) + 스냅숏 저장·복원(R16). **결정됨(2026-10-20): ① 별도 저장 ② 저장** — ① 실제 스트로크(L1 모터 위치와 약 5 mm 차)를 진값 필드로 따로 둠, ② `Measurements`도 Record에 저장(V 항목의 IMU 겉보기 기울기에 필요)
  - [x] `verify/reference` 전체 문자열 키 상수와 존재 시험(R12) (2026-10-20, `03_src/outrigger_sim/verify/reference.py`, `05_tests/unit/test_reference.py` 177건 통과; 상수 68개(자리표시 `<level>`·`<case>`·`<beta>` 전개 158경로), 파일 4개(`reference.json`, `actuator_L2_feasibility.json`, `stick_friction.json`, `v7_diagnostic.json`)별 sha256, 이 문서의 기준값 표기 37개를 파싱해 상수에 모두 포함되는지 시험)
  - [x] 전체 규모 스텝 비용 재측정(4절; 크롤러 D안 구 24개 포함, 용도별 dt 1×10⁻⁴·1×10⁻⁵ s). 부싱 회귀는 기준 파일과 같은 2×10⁻⁴ s로 한다 (2026-10-20, `04_scripts/02_chrono/solver_benchmark/step_cost_S0.py` → `06_analysis/01_chrono/step_cost_S0.json`; `make_system` 기본 SPARSE_LU+잠금, `GroundBushingCoulomb`, 패드·크롤러 바닥 패치 분리, P코어 고정. 패드 접지 190 / 195 µs/스텝(1×10⁻⁴ / 1×10⁻⁵ s, 시뮬레이션 1 s당 1.9 / 19.5 s), 크롤러 정착 71 / 74 µs(0.71 / 7.4 s). 계획 단가 0.2 ms 대비 0.95~0.98배(패드), 0.35~0.37배(크롤러). 패드 상태 비용의 72 %가 지면 부싱(Python 훅 81 µs + Chrono 부싱 하중 55 µs). OS 기본 배치는 E코어로 가 2.5배 느려짐 → 4절. NSC는 L2b 모델이 없어 재지 않았다(S7))

### S1 상부체 + 고정 다리 + 지면 부싱, 정적

- **목표**: 다리를 운용 신장 $e_{op}$에 고정하고 지면 부싱을 t = 0에 둔 상태로 수평 바닥 정적값을 맞춘다. 3단계 정착 상태를 저장한다.
- **만드는 것**:
  - `chrono/bodies`: 상부체 `auger_levels.<level>`(관성 텐서 전체), 다리 이동부 4개, 바닥(다리별 패치 + 크롤러 패치)
  - `chrono/contact`: 로드 바디에 구 1개(r = 0.06 m), 재질(R5·R8), 충돌 패밀리(R14)
  - 다리 고정: `ChLinkMotorLinearPosition` + `ChFunctionConst(e_op)`(가이드 PRISMATIC; S2b에서 함수만 $s_{ref}$로 바꾼다)
  - `chrono/probes`, `scenarios/settle`(해석 정적해 초기화), `verify/checks`의 V0~V3·V13
- **입력 키**:
  - `superstructure.auger_levels.<level>.*`
  - `legs.<leg>`: `moving_part.*`, `pad_bottom_center_retracted_m`, `attachment_point_m`, `pad.swivel_center_above_pad_bottom_m`
  - `contact.rigid_floor.L1.*`, `contact.rigid_floor.L1.derivation.operating_extension_m`
  - `contact.rigid_floor.geometry`
- **산출물**: `07_results/S1/`, `07_results/states/S1_L1_<level>.npz`, `06_analysis/01_chrono/verify_S1_L1.json`
- **통과 기준**(V1은 3단계 모두)

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V0 | 질량·무게중심·관성 = YAML. $g_n$, R8 재질, 바닥 1e9 kg, 부싱 입력 $c_t/2$, 패드 구와 패치 재질 값 같음 | 상대차 ≤ 1×10⁻⁹. **SMC 재질 값($k_n$, $g_n$, $k_t$, $g_t$, μ; Chrono float32 저장)은 float32로 반올림한 YAML 값과 정확히 같음**(사용자 결정 2026-10-20; 정적 하중 영향 ≤ 0.04 N) | YAML |
| V1 | 접촉력, 실린더 힘, 합 | 합 ≤ 1×10⁻⁴, 다리별 ≤ 1 % W/4 | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / contact_force_N`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / cylinder_force_N`, `reference.json / statics / total_weight_incl_rods_N` |
| V2 | 침투 | ±5 % | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / static_penetration_or_compression_mm` |
| V3 | roll, pitch | ±0.002° | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / static_attitude_deg (roll, pitch)` |
| V13 | 정착 10 s 뒤 정지 5 s: 자세 드리프트 < 1×10⁻⁴°, 접촉력 변동 < 0.1 % W/4, NaN 없음, 다리당 접촉점 1 | — | `dynamics_model.md` 4.5 |

- **의존**: S0.
- **위험**:
  - ① SMC 재질 합성식이 미확인이다(전·후 $k_n$이 다름). 다리별 패치로 나누고 V2로 실제 $k_n$을 역산한다.
  - ② `GetContactForce()` 프레임이 미확인이다. 로드를 기울인 단위 시험과 `ReportContactCallback` 합으로 교차 확인한다.
  - ③ 해석 정적해 초기화가 V2·V3 기준값을 그대로 쓰므로 판정이 순환할 수 있다. 판정은 10 s 정착 뒤 값으로 한다. 초기값과 같게 머무는지가 곧 평형 확인이다. 초기화 없이 ≥ 53 s 정착한 사례 1건(top)으로 같은 값에 가는지 교차 확인한다.
- **담당·작업량**: cad 중, dyn 판정 소.
- **체크리스트**
  - [x] 선행: 지면 부싱 훅 최적화(결과 불변) (2026-10-20, cad: 훅 81 → 10.6 µs/스텝, 패드 접지 1×10⁻⁴ s 193 → 116 µs/스텝(P코어, 025e445 대비 교대 4회 중앙값). 블록 6경우 궤적·상태 비트 단위 동일, 전체 규모 6.5 s 끝 상태 비트 동일. `step_cost_S0.json`의 `hook_optimization` 항목)
  - [x] V0 질량 특성 자동 비교(3단계) (2026-10-20, `verify/s1.py` `v0_checks` 91항목 × 3단계 통과. 질량·무게중심·관성 상대차 ≤ 1×10⁻⁹. **SMC 재질 kn·gn은 Chrono가 float32로 저장**(예: 20813595.4 → 20813596.0, 상대 2.9×10⁻⁸·4.2×10⁻⁸)이라 재질 항목만 float32(YAML)과 정확히 같은지로 판정했다. 정적 하중 영향 ≤ 0.04 N)
  - [x] 다리별·크롤러 바닥 패치, 재질, 충돌 패밀리(R14) API 확인 (2026-10-20, `chrono/contact.py`. pychrono 10의 API는 `GetCollisionModel().SetFamily(k)`·`DisallowCollisionsWith(k)`·`CollidesWith(k)`이고 R14에 적힌 `SetFamilyMaskNoCollisionWithFamily`는 없다. 겹친 두 구 시험으로 끈 쌍 접촉 0 확인. 패치 6개(패드 4, 크롤러 띠 2) 비중첩 검사)
  - [x] 해석 정적해 초기화 + 부싱 t = 0 (2026-10-20, `scenarios/settle.py` `analytic_static_pose`: V3 자세 + V2 침투 평균으로 원점 높이, 다리별 침투 잔차 ≤ 1.8×10⁻⁴ mm. `chrono/model.py` `L1Model`, `run_settle`)
  - [x] 패드별 수직력: 프레임 확인, 콜백 교차 (2026-10-20: `GetContactForce()`는 세계 좌표(30° 기울인 바디 시험), `ReportContactCallback` 힘은 접촉면 좌표·B 바디 기준이며 세계 변환 합이 `GetContactForce()`와 0 N 차. 위치 모터 `GetMotorForce()` + = 패드를 누르는 방향 = 실린더 힘)
  - [x] 초기화 없는 53 s 정착 교차 1건 (2026-10-20, top: V1~V3·V13 통과, 정적값 차 ≤ 2.2 N·자세 ≤ 2×10⁻⁶°. 단 영 자세 낙하 충격으로 후방 패드 부상·재접지 6건, 후방 미끄럼 약 3.9 mm, 부싱 잔류 접선 예하중 약 ±4.1~4.8 kN(합 0)이 남는다 → 해석 정적해 초기화 권장 근거)
  - [x] 정착 상태 저장(3단계) (2026-10-20, `07_results/states/S1_L1_{top,middle,bottom}.npz`, 재빌드 복원 뒤 1 s 위치 차 ≤ 1.8×10⁻¹⁵ m. 요약 `06_analysis/01_chrono/verify_S1_L1.json`, 그림 `verify_S1_L1.png`, 실행 `04_scripts/02_chrono/run_S1.py all` 약 2.5분)
  - [x] **dyn 최종 판정: 통과**(2026-10-20, `dynamics_model.md` 개정 11, 5.2절). 접촉력 − 선형 기준 최대 +66.5 N(≤ 956 N), 독립 비선형 정역학과 ≤ 0.24 N, 침투 ≤ 0.09 %, 자세 ≤ 6.1×10⁻⁵°, V13 드리프트 ≤ 2.5×10⁻⁵°·변동 ≤ 20.5 N. 67 N 차 = P-δ(무게중심 높이에 비례, 20.9 N/m). 결정: V0 재질 float32 판정(사용자 결정), 해석 초기화 기본, `stroke_true` 정의 유지. 재빌드 복원 1~4 ulp 차는 반올림이고 문제 아님

### S2a 지면 부싱 동특성 · 경사 정적

- **목표**: 모터·크롤러 없이 지면 부싱이 접선 강성·감쇠·정지 마찰을 제대로 내는지 가린다. V7 진단이 실패하면 원인이 부싱 쪽으로 좁혀진다.
- **만드는 것**:
  - `scenarios/impulse`: 이름은 뼈대 그대로 쓰고, 내용은 **초기 속도 가진**이다
  - `scenarios/slope`: 바닥 바디 회전, 레벨링 자세에서 구가 경사면에 닿은 위치에 놓고 t = 0에 부싱 생성, 중력 램프
  - `verify/metrics`: 다채널 식별(S4와 공용)
- **입력 키**: S1 전부. V12 신장은 `reference.json / slope_V12 / <case> / extension_m`을 쓴다(0.1 mm 반올림 저장값; 개정 10부터 반올림 없는 `reference.json / slope_V12 / <case> / extension_exact_m`(기준해 신장, 패드 바닥이 경사면 위)과 `reference.json / slope_V12 / <case> / extension_sphere_touch_m`(구가 경사면에 정확히 닿는 신장 = 실행 시작)이 있다). `<case>`는 `ground roll 0 deg, pitch 2 deg`, `ground roll 2 deg, pitch 0 deg`, `ground roll -2 deg, pitch 1.5 deg`다.
- **산출물**: `06_analysis/01_chrono/verify_S2a_L1.json`
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V7 진단 | 저장된 S1 top 상태에서 roll·pitch 방향 초기 속도. 1·2차 진동수, 창 ≥ 20 s | ±3 %. 약 3.06 / 4.16 Hz면 부싱 누락. ζ는 식별값에서 수치 감쇠 $\zeta_{num,i}=r_i\omega_i\Delta t/2$(부싱 변형 에너지 몫 $r_i$만 암시 적분, `dynamics_model.md` 4.3절 개정 8 검토; Δt 1×10⁻⁴ s: **6.3×10⁻⁵ / 2.3×10⁻⁴**, 2×10⁻⁴ s면 2배, V8(a) 실측이 있으면 그 값)를 뺀 뒤 판정한다(옛 값 $\omega_i\Delta t/2$ = 0.00056 / 0.00094는 SMC 접촉까지 암시로 본 과대값)(`dynamics_model.md` 개정 7 보완 V7, `v7_diagnostic.json`). **(개정 10, 안 A) 문턱·예측은 `dynamics_model.md` 5.4절 표**: ① ζ₁ 0.00705~0.00861, ζ₂ 0.0126~0.0154, ② 0.0035, ③ 0.0115, ④ 0.0162, ⑤ 0.056 / 0.005, 빼는 $\zeta_{num}$(1×10⁻⁴ s) 6.4×10⁻⁵ / 2.4×10⁻⁴ / 1.81×10⁻³. 부싱 이동 확인: 1·2차 $f$가 새 기준 1.7983 / 3.0047 Hz와 ±0.3 % 안(옛 1.786 / 2.986 Hz 근처면 부싱이 안 옮겨짐). 아래는 개정 9까지의 값(이력). ① ζ₁ 0.0070~0.0086이고 ζ₂ 0.0125~0.0153이면 정상(0.00777 / 0.0139 ±10 %). ② ζ₁ ≤ 0.0035면 $g_n$·바닥 질량 오류(예측 0.0013 / 0.0049). ③ ζ₁ ≥ 0.0115면 수직 감쇠 과대($c_n$ 2배 예측 0.0143 / 0.0230). ④ 0.0035 < ζ₁ < 0.0115이고 ζ₂ ≥ 0.0165면 $c_t$ 입력 2배 의심(R7 위반, 예측 0.0090 / 0.0187). ⑤ ④이거나 ①~④ 어디에도 들지 않으면 **yaw 초기 속도(창 2 s)로 3차(yaw-sway 5.83 Hz) ζ를 재서 확정**한다: 식별 ζ₃에서 $\zeta_{num,3}=r_3\omega_3\Delta t/2$ = 1.8×10⁻³(1×10⁻⁴ s; 2×10⁻⁴ s면 3.6×10⁻³, V8(a) 실측이 있으면 그 값)을 먼저 빼고 기준 0.0373과 비교한다, ≥ 0.056이면 $c_t$ 2배(예측 0.0744), ≤ 0.005면 부싱 감쇠 누락. $c_t$ 2배는 1·2차 ζ를 +16 % / +34 %만 올려 1·2차만으로는 확정하지 못한다 | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / V7_ball_centre_bushing_rev13 / f_damped_Hz`(앞 2개), `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / V7_ball_centre_bushing_rev13 / zeta`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / V7_ball_centre_bushing_rev13 / mode_shapes`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / V7_ball_centre_bushing_rev13 / zeta_num_r_omega_dt_half`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / V7_ball_centre_bushing_rev13 / V7_diagnostic / thresholds`. 이력(개정 9까지, 접촉점 부싱): `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / f_damped_Hz` |
| V12 | 중력 0 → $g$ 램프(2~5 s, 기본 3 s) 뒤 **정착 ≥ 53 s**(`simulation.settle_on_pads_min_s` 52.86 = τ₁ ln100, τ₁ 11.5 s; 사용자 결정 2026-10-20 — 감쇠 개정 7로 옛 10 s 뒤에는 로킹 진폭 약 42 %가 남음), **마지막 3 s 평균**의 접촉 수직력·수평력. 미끄럼 = 부싱 고정점 누적 이동 | 수직 ±1 % W/4, 수평 ±10 % 또는 ±0.2 kN, 미끄럼 < 0.1 mm, 탄성 변위 ±10 %. (개정 10, 진단) Chrono − 기준이 안 A 기대값(P-δ만)과 다리별 ≤ 3 N | `reference.json / slope_V12 / <case> / L1`, `reference.json / slope_V12 / <case> / L1_plan_A_expected_chrono_minus_reference_rev13`(기대 차, 하위 `expected_chrono_minus_reference`) |
| V13 | 위와 같음 | — | — |

- **의존**: S1.
- **위험**:
  - 중력 램프 중에도 모드가 들뜬다. 램프 길이를 1차 주기(0.56 s)의 4배 이상으로 두고, 램프 뒤 10 s 정착 + 3 s 평균으로 한다.
  - 신장 반올림(0.1 mm)이 하중에 미치는 영향은 ≤ 0.26 kN이다(검토 #8). 수평력 허용(±0.2 kN)과 같은 크기이므로 결과 보고에 함께 적는다. **(개정 9) 해당 없음**: `extension_m`은 저장용 반올림 값이고 기준해는 반올림 없는 신장으로 풀었다. 실행은 네 구가 경사면에 정확히 닿고 반올림 값과 평균 차 0인 신장을 쓴다(차 ≤ 0.044 mm, 기준해와는 강체 수직 이동만 다름, `dynamics_model.md` 5.3절 ②).
- **담당·작업량**: cad 중, dyn 판정 소.
- **체크리스트**
  - [x] 초기 속도 가진(roll, pitch, 그리고 진단 ⑤일 때 yaw 2 s) (2026-10-20, cad: `scenarios/impulse`·`verify/metrics`. S1 상단 스냅숏 복원 뒤 모드 기준점 둘레 강체 각속도(roll·pitch 0.02°, yaw 0.01° 상당, 가정), 투영 η = ΦᵀMq, 감쇠 정현 맞춤. 1차 1.7857 Hz·ζ 0.007774, 2차 2.9856 Hz·ζ 0.013894(수치 감쇠 rωΔt/2 뺀 값) → 진단 ① 정상. yaw는 2 s로 늘 돌림(판정에는 안 씀): 3차 5.8273 Hz·ζ 0.037296(기준 0.0373) → $c_t$ 입력 = $c_t/2$ 확인. 항복·사건 0)
  - [x] 경사 바닥 + t = 0 부싱 + 중력 램프 (2026-10-20, cad: `scenarios/slope`, `L1Model(floor_pose=...)`, `chrono/runs.run_gravity_ramp`. 바닥 바디를 (0, 0, z_floor) 둘레로 회전, 수평 자세·정확한 접면 신장(기준 신장과 ≤ 0.044 mm, 반올림 몫), 반코사인 램프 3 s. 시작 부싱 변형 ≤ 2.8×10⁻¹⁵ m. **초기 고정(hold)**: g = 0 출발이면 SMC 수직력이 처음 약 30 ms 동안 0이라 R15가 1 ms 뒤 부싱을 지우고 74 ms에 다시 만든다 → `attach(hold_until_loaded=True)`로 N > N_th까지 부싱 유지(기본 꺼짐, S0·S1 불변). 중력 변경도 1스텝 지연(실측))
  - [x] V12 3경우, 정착 ≥ 53 s 뒤 마지막 3 s 평균, 항복 스텝 수 기록 (2026-10-20, cad 사전 판정 통과: 수직 최대 차 +295 N(≤ 956), 수평 최대 차 11 N(≤ 200), 미끄럼 0·항복 0·사건 0, 탄성 변위 기준 면내력/k_t와 ≤ 0.05 %, V13 통과. 요약 `06_analysis/01_chrono/verify_S2a_L1.json`·`.png`, 원자료 `07_results/S2a/<case>/`, 실행 `04_scripts/02_chrono/run_S2a.py all` 약 6분. dyn 최종 판정 대기)
  - [x] **dyn 최종 판정: 통과**(2026-10-20, `dynamics_model.md` 개정 12, 5.3절). V7 진단 ①(정상), 3차 ζ 0.0373으로 R7($c_t/2$) 확정, 6개 모드 진동수 ±0.2 %·ζ ±3 %. V12 수직 차 최대 +295 / −281 N(≤ 956) = P-δ(≤ 68 N) + 구 지렛대(≤ 226 N), 독립 경사 바닥 비선형 정역학과 ≤ 1.2 N(`06_analysis/00_dynamics/s2a_slope_pdelta_check.json`). 수평 차 ≤ 11 N, 미끄럼·항복·사건 0, 탄성 변위(면내력/$k_t$) ≤ 0.07 %. V13 통과(접촉력 양자 $k_n\cdot2^{-23}$ m ≈ 2.5 N). 판단: ① hold 승인(조건부), ② 정확한 접면 신장 수용, ③ 탄성 변위 문구 정정, ④ 구 지렛대 — 부싱 작용점 볼 중심 이동(안 A) **사용자 결정 대기**, ⑤ 중력 1스텝 지연 규약 안, ⑥ 크롤러 구 접촉력 0으로 문제없음(이 단계의 "크롤러 없음" = 크롤러 접촉 없음)
  - [x] (위임, cad) hold 안전 장치 (2026-10-20, cad): `run_gravity_ramp(hold_deadline_s=램프 길이)`가 램프 끝에 hold가 남은 다리가 있으면 `HoldNotReleasedError`로 실행을 중단하고, `GroundBushingCoulomb.hold_max_tangential_N`(hold 중 최대 부싱 힘)을 기록한다. `verify/s2a.hold_checks`가 해제 시각 ≤ 램프 끝과 최대 접선력 ≤ μ$N_{th}$ = 50 N을 V12 항목으로 판정한다. 재실행 값: 해제 74.1~75.8 ms, 최대 접선력 0.37 N(pitch 2°) / 3.17 N(roll 2°) / 2.13 N(대각)
  - [x] **안 A(사용자 결정 2026-10-20)**: L1 지면 부싱 작용점을 볼 중심으로 옮기고 S1·S2a 재실행(약 6.5분, cad). dyn 몫 완료(2026-10-20, `dynamics_model.md` 개정 13, 5.4절): V7 기준값 키 `V7_ball_centre_bushing_rev13`(3단계, 수평·수직 스프링 볼 높이), 진단 문턱, V12 기대 차 `L1_plan_A_expected_chrono_minus_reference_rev13`, 신장 `extension_exact_m`·`extension_sphere_touch_m`. **cad 몫 완료(2026-10-20)**: `ground_bushing` 기본 작용점 = 볼 중심(`force_point`, 옛 동작은 `"contact_point"` 옵션), 스냅숏에 `force_point_code` 저장(키 없는 옛 스냅숏 = 접촉점, 다른 작용점 복원은 `ForcePointMismatchError`). S0 블록 회귀 영향 없음(정렬 링크로 회전 고정, 1 s 위치 차 ≤ 1.5×10⁻⁹ m). S1 4사례 재실행 통과(평균 수직력 차 ≤ 0.16 N, 스냅숏 재생성). S2a 재실행 통과: V7 1·2·3차 1.79818 / 3.00440 / 5.81462 Hz, ζ 보정 0.0078327 / 0.0139957 / 0.0372612(자동 판정은 옛 키 기준). V12 Chrono − 기준 수직 최대 +67.9 / −67.4 N, rev13 기대 차와 ≤ 0.63 N(수평 ≤ 0.11 N). ~~남은 것: `verify/reference.py` 상수(python), 재실행 dyn 판정~~ → **완료(2026-10-20)**: python 몫(rev13 상수를 `verify/reference.py`에 넣고 판정 코드를 rev13 키로 전환, V7·dt_study 재실행, V12 저장 결과 재판정, pytest 676 통과), dyn 재판정(아래 항목)
  - [x] **dyn 최종 재판정(안 A): 통과**(2026-10-20, `dynamics_model.md` 개정 14, 5.5절). V7 $f_d$ 1.79818 / 3.00439 / 5.81472 Hz(기준 −0.007 / −0.010 / −0.075 %; $f_n$끼리 ≤ 4×10⁻⁵), ζ 0.0078316 / 0.0139917 / 0.0372015(≤ +0.02 %) → 진단 ① 정상, $c_t/2$ 재확인, 부싱 이동 확인(+0.70 / +0.63 %). V12: 수직 차 = P-δ만(+67.8 / −67.4 N), 기대 차와 ≤ 0.63 N, 독립 비선형(볼 중심, `s2a_slope_pdelta_check.json` 재실행)과 수직 ≤ 0.66 N·수평 ≤ 0.11 N, 구 지렛대 제거량 = 개정 12 예측 ±1.22 N, 미끄럼·항복·사건 0, 탄성 변위 ≤ 0.07 %. hold: 해제 ≤ 75.8 ms ≤ 램프 3 s, 최대 접선력 ≤ 3.17 N ≤ 50 N. V13 통과. S1 재실행도 개정 11 판정 유효. 스냅숏 작용점 불일치 거부 방침 타당. 참고: 기준 `f_damped_Hz`는 $\lvert\lambda\rvert/2\pi$(= $f_n$)라 맞춤 $f_d$와 $\zeta^2/2$ 차(판정 무관, 판정 코드 $f_n$ 비교는 선택)
  - [x] (선택) V7 yaw 2 s를 Δt 2×10⁻⁴·5×10⁻⁵ s로 재실행 (2026-10-20, cad, 볼 중심 부싱): 식별 ζ₃ 0.040890 / 0.039077(1×10⁻⁴ s) / 0.038168, Δt 기울기 18.14 s⁻¹ = 예측 $\zeta_{num,3}/\Delta t$ 18.16 s⁻¹의 0.999배 → **부싱 암시 적분 가설과 일치**($c_t$ 배율 가설 아님). `run_S2a.py dt_study`, 요약 `verify_S2a_L1.json / v7_yaw_dt_study`. 최종 판정은 dyn(S3 V8(a)) → **dyn 판정(2026-10-20, 개정 14): 조건 ① 충족.** rev13 모드 형상 투영으로 다시 낸 값 ζ₃ 0.038107 / 0.039011 / 0.040821, 기울기 18.09 s⁻¹ / 예측 18.10 s⁻¹ = 0.999, 증분비 2.0008, 절편 0.037203 = 기준 물리 ζ. 2×10⁻⁴ s 전환은 사용자 결정 대기(S3 체크리스트)

### S2b 모터 · 크롤러 · 접지 이벤트

- **목표**: 다리를 모터로 움직이고, 크롤러 접촉을 넣고, 접지할 때 부싱을 만들고 부상할 때 없애는 이벤트 로직(R15)을 확인한다.
- **만드는 것**:
  - `chrono/actuators.L1SpeedActuator`(개정 8): **`ChLinkMotorLinearPosition` + `ChFunctionConst(s_ref)`, 훅 3단계에서 $s_{ref}\leftarrow\mathrm{clip}(s_{ref}+\mathrm{sat}(u)\Delta t,0,0.68)$**(1스텝 지연 규약, `dynamics_model.md` 4.6·5.2절 ④), 가이드 PRISMATIC, $|u|\le v_{max}$, 스트로크 끝 차단, **모터 계단 정지**. `ChLinkMotorLinearSpeed`는 내부 적분 상태가 R16 스냅숏에 담기지 않아 쓰지 않는다. 동등성: 단일 다리 시험에서 속도 ±22.67 mm/s 같음, 위치 1스텝 위상($u\Delta t$ = 2.3×10⁻⁶ m), 힘 차 $k\,u\Delta t$ ≈ 48 N. $s_{ref}$는 스냅숏에 넣고 기록에는 작용 시각 $t_n+\Delta t$로 남긴다. `ChFunctionSetpoint`는 검증 전이라 쓰지 않는다
  - 크롤러 구 배열(R13, D안): 구 24개 = 롤러 위치 12개(구 바닥 = 바닥) + 틈 있는 끝 슈 12개(구 바닥 = 바닥 + `end_shoe_gap_m`, 단방향 — 틈이 닫힌 뒤에만 접촉), 모두 상부체 바디·같은 재질
  - 접지 이벤트 부싱
  - `scenarios/stroke`(상부체 고정, 다리 공중)
- **입력 키**:
  - `actuator`: `stroke_m`, `max_speed_m_s`, `extension_direction`
  - `legs.<leg>.extension_range_m`
  - `contact.crawler.*`(R13의 키 전부: `sphere_layout.*`(`scheme`, `track_centre_y_m`, `roller_x_m`, `end_shoe_x_m`, `end_shoe_gap_m`, `sphere_radius_m`), `kn_per_sphere_N_m`, `kn_total_sensitivity_range_N_m`, `gn_per_sphere_1_s`, `damping_ratio_heave`, `damping_total_N_s_m`, `smc_material`, `collision_filter`), `simulation.settle_on_crawler_min_s`
  - `ground.crawler_bottom_z_m`
- **산출물**: `06_analysis/01_chrono/verify_S2b_L1.json`, `07_results/states/S2b_crawler_<level>.npz`(크롤러 위 정착 상태)
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V0 | 모터 +속도 1 s → 패드 −z로 $v$·1 s, 모터 반력 부호 | 부호 일치 | — |
| V0(크롤러, 개정 5 추가) | 구 개수·위치·반지름, 구당 $k_n$·$g_n$, $k_t=g_t=\mu=0$, 크롤러 패치 재질 값 같음, 로드–상부체·로드–크롤러 쌍 꺼짐 | 상대차 ≤ 1×10⁻⁹, 설정 일치. SMC 재질 값은 float32(YAML)과 정확히 같음(사용자 결정 2026-10-20) | YAML `contact.crawler.*` |
| V11 | **상부체 고정, 다리 공중**에서 큰 속도 명령과 끝을 넘는 명령 | 속도 ≤ $v_{max}(1+10^{-3})$, 위치 −1×10⁻⁴ ~ 0.6801 m, 0 → 0.68 m 시간 ±0.05 s | YAML `actuator.stroke_m`, `actuator.max_speed_m_s`, `actuator.full_stroke_time_s` |
| 이벤트 | 한 다리를 내려 접지 → 들어 올려 부상 → 재접지 | 생성·소멸 횟수가 사건 수와 같음, chatter 0 | R15 |
| 크롤러 정착 | 다리 0 m, 크롤러 정착 자세(해석해)로 초기화. 초기화하지 못하면 ≥ 65.5 s(`simulation.settle_on_crawler_min_s`) | 정착 자세 $u_z$·pitch를 기준해(D: −3.191 mm, +0.1695°)와 비교(참고, 판정은 S3 V4). 활성 구 14개(롤러 6개/측 전부 + 앞 끝 슈 1개씩; 뒤 끝 슈 3개/끝과 나머지 앞 끝 슈 2개/끝은 0. 맨 뒤 롤러열은 9.59 kN으로 하중이 가장 작다, `06_analysis/00_dynamics/crawler_layout_check.json` D 배치 `settled_on_crawler (legs at 0)` 의 `rear_row_force_N`). 크롤러 위 모드(pitch / roll / heave, D: 1.327 / 3.046 / 8.730 Hz) 진동수 기록 | `reference.json / lift_V4_compliant_crawler / layouts`, `reference.json / lift_V4_compliant_crawler / crawler_on_floor_modes (layout D, legs at 0)` |
| V13 | 모터 구속 위반 ≤ 1×10⁻⁶ m, 접촉점 수 | — | — |

- **의존**: S1(S2a와 병행 가능).
- **위험**:
  - ① 크롤러 YAML 키(`contact.crawler.*` D안, `simulation.settle_on_crawler_min_s`)는 반영됐다(2026-10-20). 값을 코드에 적지 않고 YAML에서 읽는다.
  - ② L1 모터 반력과 실린더 힘의 관계(로드 관성 포함)를 정적에서 "접촉력 − 로드 무게"와 비교한다.
  - ③ (개정 8) 강체 모터의 속도 계단은 1스텝 관성 반력 $m_{rod}\Delta v/\Delta t$를 만든다(107 kg, $\Delta v=v_{max}$: Δt 1×10⁻⁴ s 24 kN, 1×10⁻⁵ s 242 kN — 218 kN 포화 문턱을 넘을 수 있음). V11b 스텝별 포화·V17 압력을 이 스파이크로 판정하지 않는다. 권고: $u$ 가속 제한(밸브 램프, 예 0 → $v_{max}$ 0.1 s, **가정 — 사용자 확인 필요**) 또는 판정 힘에서 $m_{rod}\ddot s$ 제외. 속도 모터에도 같은 크기라 구동기 방식과는 무관
- **담당·작업량**: cad 중, dyn 판정 소.
- **체크리스트**
  - [ ] 모터 축·부호(R4)
  - [ ] 구동기 = 위치 모터 + 훅 $s_{ref}$ 적분(개정 8), 스냅숏에 $s_{ref}$ 왕복 확인
  - [ ] V11(공중 다리; 속도가 실제로 $v_{max}$에 닿는지도 확인 — `ChFunctionConst`는 속도를 구속 안정화 항으로만 주므로)
  - [ ] 크롤러 구 배열·패치·재질(R13), 패밀리(R14)
  - [ ] 접지·부상 이벤트(R15; $t_{lift}$ 1 ms, $N_{th}$ 100 N을 이벤트 시험으로 조정)
  - [ ] 크롤러 위 정착 상태 저장(3단계, 해석해 초기화. 안 되면 ≥ 65.5 s)

### S3 수치 감쇠 → 들어 올림 · 정착 → 다리 단독 신장, Δt 확정

- **목표**: Δt를 정하기 전에 수치 감쇠를 확인한다. 실제 운용 순서를 재현한다. 하중 민감도와 $F_{min}$·부상 문턱을 맞춘다.
- **만드는 것**:
  - `scenarios/lift`(개정 5 절차): $t<0$ 다리 0 m로 크롤러 위에서 정착한다(S2b 저장 상태 = 크롤러 정착 자세 초기화, 초기화하지 못하면 + ≥ 65.5 s). $t=0$에 네 모터가 동시에 $+v_{max}$로 출발한다(시각 원점 = 모터 출발). 다리마다 자기 $e_{op}$에서 **계단 정지**한다(후방 17.246 s, 전방 17.696 s). 마지막 정지 뒤 15 s 정착한다. 정지 시각과 그때 다리 속도를 기록한다. 접지 전환 구간(첫 접지 0.1 s 전 ~ 마지막 정지 0.3 s 뒤, 약 14.9~18.0 s)은 `simulation.dt_transition_s`(1×10⁻⁵ s)로, 나머지는 `simulation.L1.dt_s`(1×10⁻⁴ s)로 돈다(창 경계는 이 계획의 가정). 개정 1의 "접지 − 10 mm 출발" 안은 쓰지 않는다(시각 원점이 기준해와 달라짐).
  - `scenarios/leg_step`: FL 0.5 mm/s로 +1 / +5 mm, 0.1 mm/s 연속 신장, FL− 방향
  - `verify/metrics`: 정착값, 문턱 교차 보간, 수렴비, 접지 시각 기구학 예측 $t_i=\mathrm{gap}_i/v_{max}$(Chrono가 잰 크롤러 정착 자세에서 패드 바닥–바닥 간격)
  - `04_scripts/02_chrono/run_verify.py --jobs N`
- **입력 키**: S2b 전부, `control.F_min_cylinder_N`, `simulation.crawler_clearance_m`, `simulation.settle_on_pads_min_s`, `contact.rigid_floor.L1.derivation.operating_extension_m`(계단 정지 신장)
- **산출물**: `06_analysis/01_chrono/verify_S3_L1.json`, Δt 확정 요청(dyn 판정 뒤 YAML 재생성)

L1 기준값 경로 머리: `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top /`(아래 표의 키는 이 뒤에 붙는 전체 문자열이다).
- **통과 기준**(실행 순서대로)

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V8(a) | 감쇠 0($g_n$ = 0, 부싱 $c$ = 0), 모터 잠금, 항복 없는 작은 진폭의 초기 속도 자유 진동, **창 ≥ 60 s**, Δt와 2Δt. 접촉·솔버 설정은 본 실행과 같다(R11) | 에너지 증가 ≤ 1 % $E_{kin,0}$(에너지가 늘면 실패). 초기 속도는 roll·pitch·yaw 성분을 함께 줘 6개 모드가 모두 투영되게 한다. **모드 투영 1~6차 각각 $\zeta_{num,i}$ ≤ 0.1 × 설정 $\zeta_i$**(개정 7; 예측 $r_i\omega_i\Delta t/2$, 부싱 변형 에너지 몫 $r_i$만 암시 적분 — `dynamics_model.md` 4.3절 개정 8 검토, `06_analysis/00_dynamics/numerical_damping_review.json`. Δt 1×10⁻⁴ s 예측 6.3×10⁻⁵ / 2.3×10⁻⁴ / 1.8×10⁻³ / 1.3×10⁻³ / 2.1×10⁻⁴ / 2.3×10⁻³, 한계 7.8×10⁻⁴ / 1.39×10⁻³ / 3.73×10⁻³ / 3.63×10⁻³ / 3.24×10⁻³ / 4.94×10⁻³). **1차는 상한만** 판정한다(예측 6.3×10⁻⁵는 60 s 창에서 진폭 4 % 감소라 식별 한계 근처). **3차(yaw-sway) $\zeta_{num}$이 $r_3\omega_3\Delta t/2$(1×10⁻⁴ s: 1.8×10⁻³, 2×10⁻⁴ s: 3.6×10⁻³)의 ±30 %**인지 본다(부싱 암시 처리 가정 확인). 0에 가까우면 부싱도 명시로 도는 것이다 → 기록하고 V8(a)는 통과로 두되 2×10⁻⁴ s 복귀 조건 ①은 불충족이다. 그 밖에 ±30 % 밖이면 dyn과 원인을 본다. **$\zeta_{num}(2\Delta t)/\zeta_{num}(\Delta t)$ = 2 ± 20 %는 3차로 잰다**(1차는 너무 작아 비가 불안정). 옛 문구 "음의 수치 감쇠면 접촉 강성이 야코비안에 안 들어간 것"은 지웠다(SMC 접촉은 원래 명시이고 반암시 오일러라 에너지가 유계로 진동할 뿐 늘지 않는다) | `reference.json / time_step / L1_numerical_damping_bound_s (omega1 dt/2 <= 0.1 zeta1, top)`(옛 규칙 상한, 참고), L1 머리 + `V7_ball_centre_bushing_rev13 / zeta`(1~6차, 개정 10 안 A; 한계 7.8×10⁻⁴ / 1.40×10⁻³ / 3.72×10⁻³ / 3.62×10⁻³ / 3.23×10⁻³ / 4.91×10⁻³, 예측 L1 머리 + `V7_ball_centre_bushing_rev13 / zeta_num_r_omega_dt_half`) |
| V4 | 위 lift 절차(크롤러 = YAML D안, 같은 강성) | **다리별 접지 시각이 같은 배치·강성의 감쇠 3자유도 동적 기준해와 각각 ±0.05 s**(사용자 결정 2026-10-20; 기준 시각을 준정적에서 동적으로 바꿈): FL 15.050 / FR 15.049 / RL 15.177 / RR 15.177 s(D, `kn_total` ×1). ×3 감도 실행은 ×3 동적 기준해 15.253 / 15.253 / 15.147 / 15.146 s와 비교한다. 준정적 시각(D 15.051 / 15.049 / 15.148 / 15.148 s, ×3 15.243 / 15.243 / 15.147 / 15.146 s, 키 quasi_static_events_s)은 참고로만 기록한다. 동적 기준해의 감쇠 가정은 다리 ζ 0.03(heave 기준, YAML `cn_per_pad`)·크롤러 heave ζ 0.05, DOP853 rtol 1e-9·atol 1e-12·max_step 1 ms(같은 키 아래 meta). 다리 ζ 0.01~0.10에서 동적 시각은 ≤ 0.9 ms, 크롤러 ζ 0.02~0.3에서 ≤ 0.4 ms 움직인다(허용 ±0.05 s의 2 % 미만). 접지 = 패드 접촉력이 처음 > 0이 된 시각(R15). 접지 순서는 판정하지 않는다. 크롤러 이탈(동적 15.607 s, 준정적 15.584 s)·최종 크롤러 여유(44.93 mm)는 기록만(참고). **들어 올림 하중 판정 ②안**(사용자 결정 2026-10-20): 동적 피크는 **기록 + 상한 판정**만 한다 — 모든 다리 실린더 힘이 이동 중 포화 218 kN 미만(포화 없음). 3자유도 기준(D안 동적 141.0 kN, 준정적 119.3 kN, `leg_extension_loads.json`)과의 ±15 %는 참고로 기록만 한다. F_min 동적 여유(+18 N, ×3이면 −5.8 kN)는 개루프 V4 판정에 쓰지 않는다(접지 단계는 제어기 몫). 준정적 후방 접지는 동적 기준보다 약 29 ms 이르다(`dynamics_model.md` 3.7절, 허용의 58 %; 그래서 준정적을 기준으로 두면 Chrono가 맞아도 여유가 42 %만 남았다). 마지막 정지 뒤 V1·V3 기준. 잔류 진동 포락선 ζ ±30 %, 마지막 정지 **15 s** 뒤 roll·pitch 진폭 < 0.001°(10 s 뒤 선형 예측 pitch 1.3×10⁻³°, 15 s 뒤 3.6×10⁻⁴°) | `reference.json / lift_V4_compliant_crawler`(하위 `procedure`, `time_origin`, `layouts`, `residual_after_last_stop_linear_L1 (deg, max \|dev\| over one 1st-rocking period)`), `reference.json / lift_V4_compliant_crawler / layouts / D rollers + gapped end shoes (YAML contact.crawler.sphere_layout) / dynamic_events_s / touch_s (FL, FR, RL, RR)`, `reference.json / lift_V4_compliant_crawler / layouts / D kn_total x3 (sensitivity, YAML contact.crawler.kn_total_sensitivity_range_N_m) / dynamic_events_s / touch_s (FL, FR, RL, RR)`, `reference.json / lift_V4_compliant_crawler / dynamic_touch_damping_sensitivity` (감도, 참고) |
| V5 | 저장된 S1 상태에서 FL +1 mm, +5 mm(0.5 mm/s) 뒤 정착 | ΔF 최대 성분 ±5 %, 자세 ±5 % | L1 머리 + `dF_per_mm_FL_N`, L1 머리 + `droll_dpitch_per_mm_FL_deg` |
| V6 | FL을 0.1 mm/s로 계속 신장(FL+, FL−) | 다리 일치, 문턱 ±5 % | L1 머리 + `F_min_threshold_single_leg (cylinder force = F_min)`, L1 머리 + `liftoff_threshold_single_leg (contact force 0)` |
| V9 | Δt, Δt/2, Δt/4, 그리고 **기준해 Δt_ref = 1×10⁻⁵ s**(용도별 dt 결정, 2026-10-20). **차수(오차비)는 매끄러운 시험에서만** 잰다: ① V5 FL +1 mm 계단 응답의 과도 최대 하중(RL), ② 정착 상태에서 초기 속도 자유 진동(V7 1차)의 $t$ = 5 s 모드 진폭·위상. **V4는 차만** 판정한다. 정적 값은 Δt와 무관하므로 비를 내지 않는다 | 정적 하중 ≤ 0.1 % W/4, 최종 자세 ≤ 1×10⁻⁴°(마지막 1차 로킹 3주기 평균끼리), 과도 최대 하중 ≤ 1 %. ①·②의 오차비 2 ± 20 %. V4 접지 시각 차는 Δt 양자화(≤ 1×10⁻⁴ s)까지 허용 | `dynamics_model.md` 개정 7 V9 |
| 감도(1건) | 정지를 감속 램프로 바꾼 V4 | 기록만 | — |

- **의존**: S2a, S2b.
- **위험**:
  - ① V8(a)가 실패하면 V9와 Δt 확정을 하지 않는다. 그때는 dyn과 HHT 적분기 또는 Δt 축소를 협의한다.
  - ①-2 일반 실행 Δt는 1×10⁻⁴ s를 유지한다(사용자 결정 2026-10-20, YAML `simulation.*.dt_s` 그대로). 2×10⁻⁴ s 완화는 **조건부 검토**다: 조건 ① V8(a)에서 3차 $\zeta_{num}$이 $r_3\omega_3\Delta t/2$ 예측의 ±30 % 안(부싱 암시 가정 확인), 조건 ② 다리 ζ 0.01 감도 실행은 접선 모드(3·6차) ζ를 판정하지 않거나 5×10⁻⁵ s로 돈다(물리 ζ 약 0.012라 1×10⁻⁴ s에서도 비 0.15, 2×10⁻⁴ s에서 0.29로 10 % 규칙을 넘음). **(개정 11) 조건 ①은 S2a V7 yaw Δt 연구로 충족했다**(`dynamics_model.md` 5.5절). 2×10⁻⁴ s에서 10 % 규칙 여유는 2~3 %(3차, 세 단계)이고 경계 Δt ≈ 0.206 ms는 부싱 시정수 $c_t/k_t$ ≈ 2.0 ms로만 정해진다.
  - ② V6 0.1 mm/s는 사례당 약 150 s다. 0.5 mm/s 결과와 한 번 비교해 준정적임을 확인한 뒤 병렬로 돌린다.
  - ③ 부상(V6 FL−)에서 R15가 도는지 생성·소멸 기록으로 확인한다.
- **담당·작업량**: cad 대, dyn 판정 중(V9로 Δt 확정).
- **체크리스트**
  - [ ] V8(a) Δt·2Δt, 60 s(모드 투영 1~6차 각각 ≤ 0.1 ζ, 1차는 상한만, 3차 $\zeta_{num}$ 예측 ±30 %, 2Δt/Δt 비는 3차). **(개정 11) 3차 ±30 %와 2Δt/Δt 비는 S2a에서 충족(기록만). 판정은 에너지 비증가와 1~6차 상한, Δt는 1×10⁻⁴·2×10⁻⁴ s 두 개**
  - [ ] **결정 대기(사용자)**: (개정 11: 조건 ①은 S2a에서 충족, 질문 문안 `dynamics_model.md` 5.5절 — dyn 권고는 2×10⁻⁴ s, 단 S3 V9를 기준 Δt 2×10⁻⁴ s로 돌려 통과한 뒤 YAML 반영) V8(a)가 통과하고 조건 ①(3차 $\zeta_{num}$ 예측 ±30 %)이 확인되면 **일반 실행 Δt 2×10⁻⁴ s 복귀를 사용자에게 다시 묻는다**(조건 ②: 다리 ζ 0.01 감도 실행은 접선 모드 ζ 미판정 또는 5×10⁻⁵ s). 답을 받기 전까지 1×10⁻⁴ s, YAML은 바꾸지 않는다
  - [ ] lift(크롤러 정착 상태, t = 0 모터 출발, 다리별 $e_{op}$ 계단 정지, 정지 기록), 다리별 접지 시각 ±0.05 s 판정(**동적 기준** D: 15.050 / 15.049 / 15.177 / 15.177 s; 준정적 15.051 / 15.049 / 15.148 / 15.148 s는 참고로 함께 기록)
  - [ ] V5, V6(FL+, FL−)
  - [ ] V9(매끄러운 시험으로 차수, V4는 차만)
  - [ ] 병렬 실행기와 meta(`Params.sha256`·`Params.file_sha256`·reference sha256, dt, 솔버, pychrono 버전, 벽시계)
  - [ ] **제어 ①**(py): 개루프 명령 재생으로 runner·Record 확인(3.5절) (2026-10-20 로드맵 동기화)

### S4 6개 모드 식별 · 에너지 수지 · β 감도

- **목표**: 6개 모드의 진동수·감쇠와 감쇠·항복을 켠 에너지 수지를 맞추고, β 감도를 Chrono로 재현한다.
- **만드는 것**:
  - `verify/metrics`의 **모드 투영**(개정 5 기본): 상부체 운동을 L1은 `V7_ball_centre_bushing_rev13 / mode_shapes`(개정 10 안 A, 이력 `mode_shapes_rev5`), L2b-NSC는 `mode_shapes_rev5`의 기준점에 대한 6자유도 변위 $q$로 바꾸고 $\eta=\Phi^TMq$로 모드 좌표를 만든 뒤, 모드마다 감쇠 정현을 맞춰 진동수·ζ를 얻는다. 6채널 ERA/SSI는 교차 확인용 대안이다. `mode_content`는 에너지 비율이라 투영에 쓰지 않는다.
  - 초기 속도 가진 6종(roll, pitch, heave, surge, sway, yaw, 부싱 항복이 없는 크기): 창은 1·2차 ≥ 20 s, 3~6차 1~2 s(τ ≈ 0.3~0.4 s)
  - 에너지 항: 운동 + 중력 + SMC $\tfrac12k_n\delta^2$ + 부싱 $\tfrac12k_t|d|^2$, $D_{visc}$(부싱 실제값 = 입력의 2배), $D_{slip}$, 모터 일
  - `params` 실행 시 오버라이드(YAML은 고치지 않음). **오버라이드는 파생값을 다시 계산하지 않는다**: β 키 `actuator.oil_bulk_modulus_eff_Pa`만 바꾸면 β에서 파생된 `contact.rigid_floor.L1.kn_per_pad_N_m` 등은 그대로다. β 감도는 아래 `k_L1_N_m`을 `contact.rigid_floor.L1.kn_per_pad_N_m`의 다리별 값(필요하면 β 파생 키 전부)에 직접 오버라이드한다.
- **입력 키**: S3 전부. β 감도는 다음 키를 쓴다.
  - 강성: `reference.json / L1_beta_sensitivity_top / beta_6.9e+08 / k_L1_N_m`, `reference.json / L1_beta_sensitivity_top / beta_1.0e+09 / k_L1_N_m`, `reference.json / L1_beta_sensitivity_top / beta_1.6e+09 / k_L1_N_m`
  - 판정 값: `penetration_mm`, `static_pitch_deg`, `dF_per_mm_FL_N`, `FL+_F_min_mm`, `FL+_liftoff_mm`, `f_Hz_top_ball_centre_rev13`(개정 10 안 A; `f_Hz_top`은 접촉점 부싱 이력, 1차가 0.7 % 낮음)
- **산출물**: `06_analysis/01_chrono/verify_S4_L1.json`, β 감도 표
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V7 | 6개 모드 진동수·ζ(모드 투영) | 진동수 ±3 %, ζ ±30 % | **(개정 10, 안 A)** L1 머리 + `V7_ball_centre_bushing_rev13 / f_undamped_Hz`, `f_damped_Hz`, `zeta`(같은 머리 아래). 모드 형상: L1 머리 + `V7_ball_centre_bushing_rev13 / mode_shapes` 아래(하위 키 이름은 이력 `mode_shapes_rev5`와 같음) `Phi (rows = coordinates, cols = modes in f_undamped_Hz order, first 6)`, `mass_matrix (same coordinates)`, `reference_point_m (rotations about it, translations of it; body axes, level body = world)`, `coordinates`, `projection` |
| V8(b) | V12 + 큰 수평 초기 속도(항복 발생)에서 에너지 수지 | 잔차 ≤ 1 %, $D_{slip}/\sum\mu N|\Delta a|$ 1.00~1.05. 부싱 생성·소멸 횟수 기록 | — |
| β 감도 | 개정 5 규칙: 바꾸는 것은 L1 패드 $k_n$(`k_L1_N_m`) 하나뿐이다. **$c_n$, $c_t$, $g_n$, 부싱 $k_t$는 기본값 그대로.** 판정은 정적값(침투, 정착 pitch, FL +1 mm ΔF, FL+ $F_{min}$·부상 문턱)과 **비감쇠 진동수**(`f_Hz_top`)만 한다. ζ는 판정하지 않는다. V6는 비용이 크면 1.6 GPa 한 값만 돌린다(0.69 GPa는 약 200 s) | V2·V3·V5·V6·V7 진동수와 같은 허용 | 위 β 키 |

- **의존**: S3(Δt 확정).
- **위험**: 5.8~8.0 Hz 네 모드가 가깝다. 모드 투영으로 분리하고, 투영 잔차(다른 모드 섞임)가 크면 ERA/SSI로 교차 확인한다. $\Phi$는 기준해 강성(Chrono 입력과 같은 $k_n$, $k_t$)에서 나온 값이므로, β 감도처럼 강성을 바꾼 실행에는 쓰지 않고 ERA/SSI를 쓴다.
- **담당·작업량**: cad 중, dyn 판정 중.
- **체크리스트**
  - [ ] 초기 속도 6종 + 모드 투영($\Phi$, $M$, 기준점) + ERA/SSI 교차
  - [ ] V8(b) 에너지 수지
  - [ ] β 3값(감쇠 고정), V6는 비용에 따라 1.6 GPa만
  - [ ] 다리 감쇠비 감도 양끝(ζ 0.01 / 0.10, `00_docs/01_dynamics/damping_survey.md`) (2026-10-20 로드맵 동기화)
  - [ ] (선택) 로드측 챔버 +10 % $k_v$ 1건

### S5 오거 3단계

- **목표**: 상단·중단·하단에서 정적 하중과 로킹 진동수를 확인한다.
- **만드는 것**: 레벨을 시나리오 매개변수로 노출한다. 오거 합성 검사(`fixed_part` + `auger_moving_set_at_cad_pose`를 z로 Δ 이동 → `auger_levels.<level>`)를 단위 시험으로 둔다.
- **입력 키**: `superstructure`: `auger_levels.*`, `auger_moving_set_at_cad_pose.*`, `fixed_part.*`, `auger_level_order`
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V0(오거) | 합성 질량·무게중심·관성 = `auger_levels.<level>` | ≤ 1×10⁻⁹ | YAML |
| V10 | 저장된 S1 상태(3단계)에서 V1, roll·pitch 초기 속도(창 ≥ 20 s)로 1·2차 | 하중 ≤ 0.1 % W/4, 진동수 ±3 %, 상단 < 중단 < 하단 | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / contact_force_N`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / V7_ball_centre_bushing_rev13 / f_damped_Hz`(앞 2개, 개정 10 안 A: 1차 1.798 / 2.333 / 2.893 Hz, 2차 3.005 / 3.536 / 3.959 Hz) |

- **의존**: S4(식별 도구).
- **담당·작업량**: cad 소, dyn 판정 소.
- **체크리스트**
  - [ ] 오거 합성 단위 시험
  - [ ] 3단계 V1·V7(1·2차), V10

### S6 압력 센서 · 힘 포화 · 제어기 경계

- **목표**: 제어기가 보는 관측과 주는 명령을 엔진 독립 형식으로 고정한다. 210 bar 힘 포화를 구현하고 350 bar 지표를 기록 경로에 넣는다.
- **만드는 것**
  - cad:
    - `sensors/truth`: IMU 장착점 비력·각속도 진값(장착점 기본값 = 캐빈 바닥 아래 상부 프레임, 기체 좌표 (0.31, 0.88, 0.040) m, BASE DECK 좌측 폰툰 15 mm 가로판 윗면, 후보 C1, 2026-10-20 사용자 결정, `00_docs/00_cad/cad_origin_mass_imu.md` 4절, 그림 `01_cad/01_parts/imu_c1_*.png`. 인자로 바꿀 수 있게 둔다), 헤드 압력 $p=F_{cyl}/A_p$, 스트로크(모터 위치, 보정값 = 모터 위치 − $F_{cyl}/k_{oil}(e)$)
    - 힘 포화: 구동기 모델 안에서 **물리 스텝마다** 판정한다. $F_{cyl}\ge$ `actuator.max_force_extend_N`이고 $u>0$이면 $u=0$. $F_{cyl}\le$ −`actuator.max_force_retract_N`이고 $u<0$이면 $u=0$. 제어 주기(20 ms)로만 판정하면 9.4 kN이 넘친다.
    - 단일 다리 시험 모델: 패드를 바닥에 **$k_n$과 같은 강성의 양방향 스프링**(`ChLinkTSDA` 또는 부싱 축 방향, 감쇠 = $c_n$ 실제값)으로 묶는다. 강체로 묶으면 강체 모터와 직렬이라 힘이 부정이 된다. 접촉으로는 수축 시험의 인장을 낼 수 없다.
    - `runner`: 제어 주기 영차 유지(기본 20 ms = 200스텝, Δt 1×10⁻⁴ s)
  - py: IMU 오차 모델, `Controller` 프로토콜, 빈 제어기·재생 제어기
  - py(S6 뒤 폐루프, 3.5절):
    - IMU 오차 모델 센서 등급(축마다 같은 부호 바이어스, 영점 오차 = 각도 / 비력): 우수 영점 후 0.046°(0.80 mg, 15 µg/√Hz), 보통 영점 후 0.072°(1.26 mg, 82 µg/√Hz), 보통 영점 후 + 반복성 0.122°(2.13 mg), 보통 출하 0.17°(2.97 mg, 영점 교정 없음 — 의무 절차 위반 경우의 참고). 이상(0°, 15 µg/√Hz)은 기준선. 값은 `imu_cabin_and_accuracy_review.md` 4.1절.
    - 자세 신호 필터: 2차 저역통과 = 1차 τ 0.5 s × 2단(약 0.32 Hz). 완료 판정 데드밴드 0.03°.
    - 제어기 C2(잠정 확정): 기구학 분해 $u=A[\dot z,\dot\phi,\dot\theta]^T+n\dot\tau$, $n$ = (0.476, −0.476, −0.523, 0.523), 자세 PI, 압력 기반 비틀림 루프($n^TP\to0$) + $F_{min}$ 가드. 대안 C8(2상)도 같은 경계로 돌릴 수 있게 둔다.
    - 결합 접지 판정: 물리 기반 판정기(압력·스트로크·자세. 증분 강성 Δp/Δs, 자세 반응과 기구학 J의 일치, 마찰 이력 띠) + 레벨링 중·후 탐침(다리 수 mm, 자세 변화 ±0.1° 안). ML/DL 판정기는 비교 후보이고 Chrono 접촉력을 라벨로 쓴다(S7·S8 데이터, 3.5절).
- **입력 키**:
  - `actuator`: `bore_diameter_m`, `annulus_area_m2`, `max_force_extend_N`, `max_force_retract_N`, `relief_pressure_moving_Pa`, `locked_pressure_limit_Pa`, `lock_valve`, `oil_bulk_modulus_eff_Pa`, `oil_dead_length_m`
  - `sensors.cylinder_pressure.*`, `control.*`
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V11b | 단일 다리: 신장 포화 도달 후 정지, 수축 당김 포화 | 포화 뒤 힘 ≤ 포화값 × 1.01, 명령 방향 이동 ≤ 0.01 mm, 반대 명령 즉시 추종 | `reference.json / hydraulic_circuit / max_head_force_N`, `reference.json / hydraulic_circuit / max_rod_side_force_N` |
| V17(경로) | 저장된 S1 상태에서 잠긴 압력 기록, 350 bar 초과 시각·다리·최대값 보고 | 외란 없는 정착에서 최대가 정적 최대 압력과 같음 | `reference.json / hydraulic_circuit / max_static_head_pressure_Pa`, YAML `actuator.locked_pressure_limit_Pa` |
| 센서 진값 | 정지 수평에서 IMU 비력 = +g(장착점 회전 반영), 압력 = 실린더 힘 / $A_p$ | 상대차 ≤ 1×10⁻⁶ | 유도 |
| V13 | 제어 주기 영차 유지에서 NaN 없음 | — | — |

- **제어기 검증 항목**(S6 뒤 L1 폐루프, py 실행 → dyn 판정. 출처 `control_candidates_comparison.md` 7.3절, 목표값·장착점·등급은 개정 3 결정으로 바꿈. 판정 기준은 제안이다):

| # | 항목 | 방법 | 판정 기준(제안) |
|---|---|---|---|
| 1 | 축소 모델 대조 | C2를 상단 수평·대각 3°·roll +3°로 실행해 축소 모델의 시간·최소 하중·최종 하중과 비교 | 접지 후 시간 ±10 %, 최소 하중 ±5 kN, 최종 하중 다리별 ±1 % W/4 |
| 2 | ±0.2° 정확도 | IMU 장착점 (0.31, 0.88, 0.040) m(C1), 2차 필터, 데드밴드 0.03°, 센서 등급 이상 / 우수 영점 후 / 보통 영점 후 / 보통 영점 후 + 반복성 / 보통 출하. 오거 3단계 × 경사 4가지 | 정상상태 실제 자세(준비 완료 뒤 마지막 5 s 최대 절대값) + 장착 몫 0.02°(C1 프레임 직접 장착, 2026-10-20 결정; 이전 0.03°) ≤ 0.2°. 축소 모델 기대(C2, 장착 몫 더함): 우수 0.089°, 보통 0.117°, 보통 + 반복성 0.178°는 통과, 보통 출하 0.222°는 불가. Chrono 시뮬레이션은 장착 몫을 모델에 넣지 않으므로 판정 때 더한다 |
| 3 | $F_{min}$ | 크롤러 이탈 뒤 모든 시각의 실제 실린더 힘 | ≥ 9.453 kN. 최소값과 시각 보고 |
| 4 | 210 bar 포화 | 물리 스텝마다 판정 경로(V11b) 동작, 레벨링 중 최대 압력 | 통과 실행 ≤ 150 bar |
| 5 | 로킹·필터 | 1 s 이동 평균 제거 실제 자세 진폭, 장착점 IMU 겉보기 기울기, 2차 필터 뒤 잔류 | 실제 진폭 ≤ 0.06°. 필터 뒤 잔류 ≤ 0.005°(축소 모델 해석 0.0024°, 목표는 **가정**). 겉보기 기울기 증폭을 `imu_cabin_and_accuracy_review.md` 2.2절(1차 +27~+87배, 2차 +130~+361배)과 비교 |
| 6 | 비틀림 외란 | 레벨링 뒤 RR 지면 11.5 mm 침하(강체 지면이면 고정점 이동), $F_s$ 0(L1) | 회복 후 모든 다리 ≥ $F_{min}$ |
| 7 | 탐침·결합 접지 판정 | ±2 mm 탐침의 자세 변화, 증분 강성 판정, 소요 시간. 물리 기반 결합 판정 결과를 Chrono 접촉력(진값)과 대조 | 자세 변화 ≤ 0.1°(탐침 한도는 목표와 별개로 유지), 접지 판정 일치 |
| 8 | 오거 3단계 | 상단·중단·하단 | 축소 모델 3.1절과 같은 경향 |
| 9 | (S7·S8, L2b) 압력만 vs 결합 판정 | $F_s$ 0/2/5/12 kN, 침하 시나리오 | 축소 모델 5.3절 표 재현. 압력만 판정의 놓침이 L2b에서도 생기는지 |

- **의존**: S3(S4·S5와 병행 가능).
- **위험**:
  - ① 제어기가 진값을 읽는 누수: runner가 `Measurements`만 넘긴다.
  - ② IMU 장착점은 캐빈 바닥 아래 상부 프레임으로 정했지만 좌표는 CAD 면 탐색으로 (0.31, 0.88, 0.040) m(C1)로 정했다(2026-10-20 사용자 결정; 이전 bbox 가정 (0.20, 0.88, 0.30) m는 붙일 면이 없었음). 로킹 순간 회전 중심이 IMU 아래 2.0~5.8 m(지면 아래)라 높게 달수록 겉보기 기울기 증폭이 커진다. 장착점은 인자로 받고, 실기 좌표가 오면 바꾼다. 캐빈 몸체(방진 마운트 위)에는 달지 않는다.
  - ③ L1 스트로크와 실제 스트로크가 약 5.1 mm 다르다. 두 신호를 모두 낸다.
- **담당·작업량**: cad 중, py 중, dyn 판정 소.
- **체크리스트**
  - [ ] `Measurements`·`Command` 타입 확정(py 검토)
  - [ ] 압력·스트로크 가상 센서
  - [ ] 스텝별 힘 포화 + 양방향 스프링 단일 다리 V11b
  - [ ] 350 bar 지표 기록
  - [ ] py: IMU 오차 모델, Controller 프로토콜, 빈 제어기로 60 s 폐루프 연기 시험
  - [ ] IMU 진값 장착점 기본값 (0.31, 0.88, 0.040) m(C1, 2026-10-20 결정)과 인자 변경 단위 시험
  - [ ] py: 센서 등급 5종(이상·우수 영점 후·보통 영점 후·보통 + 반복성·보통 출하), 2차 필터(τ 0.5 s × 2)
  - [ ] py: C2 제어기(대안 C8)와 물리 기반 결합 접지 판정 + 탐침
  - [ ] 제어기 검증 항목 1~8(L1), 9는 S7·S8

### S7 L2b-NSC

- **목표**: 운용안 B 재판정 모델을 만든다. L1과 같은 시나리오(초기 조건 규칙, 초기 속도 가진, 중력 램프 포함)로 L2b-NSC 열을 통과시키고 V14를 판정한다.
- **만드는 것**:
  - `params` 모델 선택: `load_params(..., model="L2b_NSC")` 인자와 L2b 타입(`contact.rigid_floor.L2b_NSC`, `actuator.L2b_NSC`, `simulation.L2b_NSC`)을 추가한다(S0에서 미룸)
  - `make_system("L2b_NSC")`: PSOR 50회, μ 0.5, 크롤러 NSC μ = `contact.crawler.friction`
  - `L2bForceActuator`: $s_{ref}$ 적분, $F=k_{ax}(s)(s_{ref}-s)+c_{oil}(\dot s_{ref}-\dot s)$, 스텝별 210 bar 포화
  - 횡 부싱(입력 $c_t/2$), 가이드 x·y 해제
- **입력 키**:
  - `contact.rigid_floor.L2b_NSC.*`, `actuator.L2b_NSC.*`, `simulation.L2b_NSC.dt_s`
  - `actuator`: `oil_bulk_modulus_eff_Pa`, `oil_dead_length_m`, `frame_stiffness_N_m`, `bore_diameter_m`
  - `contact.rigid_floor.L1.derivation.k_rod_N_m`, `contact.rigid_floor.concrete.k_N_m`
- **통과 기준**:
  - V0~V13 전부를 L1과 같은 방법·허용으로 판정한다.
  - 기준값 경로는 `reference.json / chrono_test_references / L2b_NSC_force_motor_axial_spring_lateral_bushing / levels / <level> / <항목>`이다.
  - `f_undamped_Hz`, `f_damped_Hz`, `zeta`는 10개 값이다. **앞 6개(상부체 모드)만** 쓴다. 뒤 4개는 NSC 강체 접촉을 근사한 인공 모드다.
  - V12는 `reference.json / slope_V12 / <case> / L2b_NSC`다. V2는 축 스프링 압축으로 판정한다(NSC 침투 ≈ 0).
  - V7 모드 투영은 `reference.json / chrono_test_references / L2b_NSC_force_motor_axial_spring_lateral_bushing / levels / <level> / mode_shapes_rev5`를 쓴다(Φ 열은 앞 6개 모드).

| V | 판정 | 허용 | 기준값 |
|---|---|---|---|
| V4(NSC) | L1과 같은 lift 절차. 크롤러(D안 구 24개)가 NSC 강체라 가라앉지 않는다 | **다리별 접지 시각 ±0.05 s**: FL 15.382 / FR 15.382 / RL 15.040 / RR 15.040 s(강체 크롤러 극한(`kn_total` ×10³)의 감쇠 3자유도 동적 기준해, 사용자 결정 2026-10-20. 준정적 15.375 / 15.375 / 15.040 / 15.040 s는 참고. 크롤러 ζ를 0.02~1(거의 소성 충돌, NSC처럼 되튐 없음)로 바꿔도 0.05 ms 안이라 NSC 무반발 접촉과의 차는 판정에 영향이 없다. 후방이 닿은 뒤 상부체가 앞 롤러열을 축으로 숙여 전방이 강체 기구학 15.49 s보다 빨리 닿는다). 나머지는 L1 V4와 같음 | `reference.json / lift_V4_compliant_crawler / layouts / D rigid crawler limit (kn_total x1e3, L2b-NSC V4) / dynamic_events_s / touch_s (FL, FR, RL, RR)` |
| V13(NSC) | PSOR 50회에서 정지 5 s 접촉력 변동 | ≤ 0.1 % W/4 | `dynamics_model.md` 5절 |
| V14 | 최대 레벨링 경사 3경우(pitch +3.86°, roll 5.91°, 대각 3.31°)에서 V12 절차 + **RL 단독 신장(RL+)** 민감도·$F_{min}$ 문턱·부상 문턱 + 로킹. FL+는 pitch+에서 FL이 스트로크 끝이라 할 수 없다. RL+는 세 경우 모두 스트로크 여유가 있다 | 민감도·문턱 ±5 %, $F_{min}$ 도달 다리 일치, 진동수 ±3 %, 미끄럼 < 0.1 mm | `actuator_L2_feasibility.json / A_extension_dependence / V14_rev5`(하위 `method`, `V14_test_leg`, `cases`) |

- **의존**: S6, S4의 식별·에너지 도구.
- **위험**:
  - ① 가이드 해제: 헤더에 `SetGuideConstraint(cx, cy, crx, cry, crz)`가 있다(`ChLinkMotorLinear.h:42`). Python 노출은 미확인이다. 안 되면 FREE 가이드 + `ChLinkLockAlign`으로 한다.
  - ② 힘 법칙을 양해로 갱신한다(양해 안정 한계 $2/\omega$ = 1.1×10⁻³ s ≫ 일반 실행 1×10⁻⁴ s, 기준해·전환 1×10⁻⁵ s). 문제가 보이면 `ChLinkTSDA`(자유 길이 = $s_{ref}$)로 바꾼다.
  - ③ PSOR 반복 오차가 V1·V13을 못 맞추면 반복 수를 올리고 비용을 다시 잰다.
  - ④ 크롤러 접지 구간은 NSC 강체 다점 접촉이라 하중이 부정이다. 이 구간 하중은 판정하지 않는다.
  - ⑤ NSC 패드별 수직력 읽기는 V1로 교차 확인한다.
- **담당·작업량**: cad 대, dyn 판정 중.
- **체크리스트**
  - [ ] 가이드 x·y 해제 API 확인
  - [ ] 힘 법칙, $s_{ref}$, 스텝별 포화
  - [ ] 횡 부싱
  - [ ] V0~V13(배열 앞 6개)
  - [ ] V4(NSC, 다리별 동적 기준 15.382 / 15.382 / 15.040 / 15.040 s; 준정적 15.375 / 15.375 / 15.040 / 15.040 s 참고)
  - [ ] V14 3경우, RL+(`V14_rev5`)
  - [ ] L1 대 L2b-NSC 비교표
  - [ ] **제어 ③ 준비**(py): S6 제어기로 L2b-NSC 폐루프 연기 시험 (2026-10-20 로드맵 동기화)

### S8 실 마찰 · 카운터 밸런스 · D2 외란

- **목표**: L1로 볼 수 없는 압력 판독 오차(실 마찰)와 잠김 압력 한계를 판정한다.
- **만드는 것**:
  - 실 마찰 요소: 기름 스프링에만 병렬인 Coulomb $|f|\le F_s$, 부싱과 같은 탄소성 복귀 사상
  - 카운터 밸런스 요소(`dynamics_model.md` 4.4)
  - L1용 같은 처리(모터 위치에서)
  - `chrono/loads` D2: 마스트 축에 하향 계단·램프 힘, accumulator
  - `scenarios/disturbance_d2`: 저장된 정착 상태에서 시작
- **입력 키**: S7 전부, `actuator.locked_pressure_limit_Pa`, `actuator.lock_valve`, D2 크기·시간·작용점(**사용자 결정**)
- **통과 기준**

| V | 판정 | 허용 | 기준값 |
|---|---|---|---|
| V15(a) 상승 | $F_s$ = 0 / 2 / 5 / 12 kN, 초기 $f$ = 0, 나머지 다리 잠금, 0.1 mm/s. FL $s_{ref}$를 0에서 **첫 패드 접촉력이 0이 될 때까지**(단방향 접촉, 그 뒤는 판정하지 않음). 실제 하중 $F_{min}$ 문턱, 압력 $F_{min}$ 문턱(또는 "도달 안 함"), 부상 문턱·다리, 부상 순간 압력 판독 | 문턱 ±5 %, 부상 다리 일치, 압력 판독 ±0.3 kN. $F_s$ 12 kN에서는 압력이 $F_{min}$에 닿기 전에 RL이 뜨는 것이 기준해다 | `actuator_L2_feasibility.json / C_seal_friction / V15_rev5 / a_upsweep_unilateral` |
| V15(b) 왕복 | 같은 조건으로 FL $s_{ref}$ 0 → 10 → 0 mm(어느 다리도 $F_{min}$·부상에 닿지 않음). 왕복 뒤 잔류 실제 하중/압력(다리별) | 잔류 ±10 % 또는 ±0.3 kN 중 큰 값 | `actuator_L2_feasibility.json / C_seal_friction / V15_rev5 / b_roundtrip_10mm`. 기존 0 → 16 → 0 mm 값(`runs`)은 양방향 접촉이라 쓰지 않는다 |
| V17 | D2 외란에서 모든 다리·시각 $p_i$ ≤ 350 bar(파일럿 체크). 카운터 밸런스면 밀림량 | 판정 지표(초과 보고) | YAML `actuator.locked_pressure_limit_Pa` |
| V8(b) | 실 마찰·카운터 밸런스 소산을 포함한 에너지 수지 | 잔차 ≤ 1 % | — |

- **의존**: S7. V17의 L1 실행은 S6 뒤 가능하지만 D2 결정이 먼저다.
- **위험**:
  - ① 마찰 초기 상태 $f=0$ 가정이 결과를 바꾼다. 기록하고 dyn이 판단한다.
  - ② ζ(Q6, 결정됨: 다리 축 0.03, 감도 0.01~0.10)가 D2 계단 응답의 공진 크기를 정한다(1차 로킹 ζ 0.0078이면 공진 증폭 약 64배). 감도 양끝(0.01, 0.10)을 함께 돌린다. 하중 피크 구간은 `simulation.dt_transition_s`(1×10⁻⁵ s)로 돈다.
  - ③ V15(a)는 부상에서 끝나므로 R15 이벤트(부상 판정 $t_{lift}$ 1 ms)가 문턱 판정 시각을 늦출 수 있다. 부상 문턱은 접촉력 0 교차 시각(보간)으로 재고 이벤트 시각과 따로 기록한다.
  - ④ 기준해는 로드 무질량·잠김 강성 2.17×10⁸ N/m 가정이다. 0.1 mm/s에서도 로드 관성 효과가 남는지 0.05 mm/s 1건으로 확인한다.
- **담당·작업량**: cad 대, dyn 판정 중.
- **체크리스트**
  - [ ] 실 마찰 요소 + V15(a) 단방향 상승(부상까지), V15(b) 0 → 10 → 0 mm 왕복
  - [ ] 카운터 밸런스 옵션(`lock_valve`)
  - [ ] D2 하중(결정 뒤)
  - [ ] V17 L1·L2b-NSC
  - [ ] **제어 ③**(py): 큰 경사·실 마찰(F_s 0/2/5/12 kN)·D2 재판정, S6 제어기 검증 항목 9(압력만 vs 결합 접지 판정) (2026-10-20 로드맵 동기화)
  - [ ] **접지 판정 ML/DL**(py): Chrono 접촉력 라벨 학습 데이터 생성(F_s·β·경사·오거·노이즈 무작위화) → `pytorch_214_cuda_python_313`에서 학습 → 물리 기반 판정기와 비교 (2026-10-20 로드맵 동기화)

### S9 SCM 연약 지면 (파라미터 확보 후)

- **목표**: 패드 침하로 자세가 흐트러지는 상황을 재현한다.
- **만드는 것**:
  - 패드 바디 분리(`pad_body`, `rod_body`), `ChLinkLockSpherical`(볼 중심), 경사 범위 ±10° 제한(방식은 dyn과 협의)
  - 팔각 패드 충돌 메시
  - `pychrono.vehicle.SCMTerrain`(설치본에 있음, 2026-10-19 확인)
  - $k_{ax}$에서 콘크리트를 뺀다
  - SCM 격자 수렴 시험
- **입력 키**:
  - `legs.<leg>`: `pad_body.*`, `rod_body.*`, `pad.polygon_xy_m`, `pad.thickness_m`, `pad.swivel_tilt_range_deg`
  - SCM 파라미터(**미정**)
- **통과 기준**

| V | 판정 | 허용 | 기준값 |
|---|---|---|---|
| V0 | pad_body + rod_body = moving_part | ≤ 1×10⁻⁹ | YAML, `02_params/rexome33_checks.json` |
| V16 | 파라미터 확정 전: 합력 상대차 ≤ 1×10⁻³, 에너지 증가 없음. 확정 후: Bekker 평판 식 | 확정 뒤 dyn이 정함 | `dynamics_model.md` 5절 |

- **의존**: S7(+S8 선택). **SCM 파라미터 결정이 선행 조건**이다.
- **위험**: SCM 격자 비용과 시간 간격이 미측정이다. 침하가 남은 스트로크(0.279 / 0.289 m)를 넘을 수 있다.
- **담당·작업량**: cad 대, dyn 판정 중.
- **체크리스트**
  - [ ] SCM 파라미터 확보
  - [ ] 패드/로드 분리 + 구면 조인트 + 경사 제한
  - [ ] 단일 패드 비용·격자 수렴
  - [ ] V16
  - [ ] **제어 ④·접지 판정**(py): 연약 지면 재판정(크롤러 토양 ζ 0.2) (2026-10-20 로드맵 동기화)

## 3. 코드 구조

### 3.1 현재 상태와 계획 모듈

패키지는 설치하지 않는다. pytest는 `pyproject.toml`의 `pythonpath = ["03_src"]`로, 스크립트는 경로 추가로 `03_src/`를 불러온다.

| 경로 | 상태(2026-10-20) | 내용 |
|---|---|---|
| `pyproject.toml` | **있음** | 도구 설정만 둔다. pytest(`minversion 8.0`, `pythonpath = ["03_src"]`, `testpaths = ["05_tests"]`, `--strict-markers`, 마커 `chrono`·`sim`·`slow`)와 ruff(줄 100, py312, isort first-party `outrigger_sim`) |
| `03_src/outrigger_sim/__init__.py` | **있음**(docstring만) | 엔진 독립 핵심 + Chrono 백엔드 |
| `03_src/outrigger_sim/chrono/__init__.py` | **있음** | Chrono 백엔드 패키지. 계획 모듈: `lateral_bushing`(S7), `actuators`(S2b), `loads`(S8), `scm`(S9) |
| `03_src/outrigger_sim/chrono/system.py` | **있음**(S0) | `make_system`(SPARSE_LU + 패턴 고정 기본), `set_gravity`, `select_time_step` |
| `03_src/outrigger_sim/chrono/ground_bushing.py` | **있음**(S0) | `GroundBushingCoulomb`: 지면 고정 구면 부싱 + 원형 Coulomb 복귀 사상, R15 부상·재접지 |
| `03_src/outrigger_sim/chrono/snapshot.py` | **있음**(S0) | R16 Chrono 쪽 스냅숏 채우기·복원(`ChLinkMotorLinearSpeed` 거부) |
| `03_src/outrigger_sim/chrono/bodies.py` | **있음**(S1) | 상부체(오거 level, 관성 텐서 전체)와 다리 이동부 4개 |
| `03_src/outrigger_sim/chrono/contact.py` | **있음**(S1) | 패드 구·바닥 패치(패드 4, 크롤러 띠 2)·SMC 재질(R5·R8)·충돌 패밀리(R14, `DisallowCollisionsWith`)·접촉 보고 콜백 |
| `03_src/outrigger_sim/chrono/probes.py` | **있음**(S1) | 스텝마다 상태 1회 복사(R9), `TruthState`(`stroke_true_m` = 모터 − $F_{cyl}/k_{oil}$) |
| `03_src/outrigger_sim/chrono/model.py` | **있음**(S1) | `L1Model`: 바디·접촉·위치 모터(상수 함수)·지면 부싱 조립, 훅 순서(4.6절), V0 인벤토리, `operating_extensions_m`, `zero_pose` |
| `03_src/outrigger_sim/geometry.py` | **있음**(S1) | 엔진 독립 기하: 신장별 패드·볼 중심 위치, 패드가 막 닿는 원점 높이 |
| `03_src/outrigger_sim/hostcpu.py` | **있음**(S1) | 하이브리드 CPU 배치: P코어 고정 + EcoQoS 해제(6절 #24) |
| `03_src/outrigger_sim/scenarios/settle.py` | **있음**(S1) | 해석 정적해 초기화(`analytic_static_pose`, 2절 규칙 1), 정착·정지 창 |
| `03_src/outrigger_sim/verify/checks.py` | **있음**(S1) | `CheckResult`, 비교 도우미(상대·절대·같음) |
| `03_src/outrigger_sim/verify/s1.py` | **있음**(S1) | S1 V0(재질 float32 판정 포함)·V1~V3·V13 |
| `03_src/outrigger_sim/control/__init__.py` | **있음**(docstring만) | Controller 프로토콜과 제어기(py) |
| `03_src/outrigger_sim/scenarios/__init__.py` | **있음**(docstring만) | `settle` 있음(S1). 계획 모듈: `lift`, `leg_step`, `impulse`(초기 속도 가진), `slope`, `stroke`, `single_leg`, `disturbance_d2` |
| `03_src/outrigger_sim/sensors/__init__.py` | **있음**(docstring만) | 계획 모듈: `truth`(cad), `imu_model`(py) |
| `03_src/outrigger_sim/verify/__init__.py` | **있음**(docstring만) | `checks`·`s1` 있음(S1). 계획 모듈: `metrics` |
| `03_src/outrigger_sim/verify/reference.py` | **있음**(S0) | 기준값 전체 문자열 키 상수 `RefKey`·`References`(R12), 파일 SHA-256 지문. 키 존재는 `05_tests/unit/test_reference.py`가 이 계획 문서의 백틱 경로와 대조한다 |
| `03_src/outrigger_sim/params.py` | **있음**(S0) | 파라미터 로더 `load_params()` |
| `03_src/outrigger_sim/{frames, signals}.py` | **있음**(S0) | 좌표, 신호 타입·Record 스키마 |
| `03_src/outrigger_sim/engine.py` | **있음**(S0) | SimEngine 프로토콜, 엔진 독립 `Snapshot`·호환 검사(R16), 엔진 상태 예외. pychrono를 import하지 않는다. Chrono 구현체는 아직 없다 |
| `03_src/outrigger_sim/record.py` | **있음**(S0) | Record(npz + meta.json, `stroke_true` 포함)·스냅숏 파일 저장 |
| `03_src/outrigger_sim/runner.py` | 계획(S6) | 실행기(영차 유지) |
| `05_tests/conftest.py` | **있음** | 세션 픽스처 `project_root`, `params_path` |
| `05_tests/unit/` | **있음** | `test_params.py`, `test_frames.py`, `test_signals.py`, `test_engine.py`, `test_reference.py`(3.4절) |
| `05_tests/chrono/` | **있음** | `test_system.py`(R1·R2·R6·R11 시스템 팩토리), `test_smc_damping.py`(SMC Hooke 감쇠 규약), 마커 `chrono` |
| `05_tests/verify/` | **있음**(`.gitkeep`만) | 3.4절 V 시험 자리 |
| `04_scripts/02_chrono/run_S1.py` | **있음**(S1) | S1 4사례(사례마다 별도 프로세스, P코어 고정) + 요약 `06_analysis/01_chrono/verify_S1_L1.json`·그림 |
| `05_tests/chrono/test_model_S1.py`, `05_tests/unit/test_settle.py`, `05_tests/verify/test_S1_L1.py` | **있음**(S1) | S1 모델·해석 초기화·V 판정 시험 |
| `04_scripts/02_chrono/run_verify.py` | 계획(S3) | 단계별 V 실행기 |
| `04_scripts/02_chrono/test_stick_friction.py` | 있음 | S0 회귀 기준으로 그대로 둔다 |

계획 모듈의 역할:
- `params`: YAML을 고정 dataclass로 읽는다. 수치는 float으로 강제한다(문자열 수치 변환, 변환 불가·필수 키 누락은 키 경로를 담은 예외). 오거 level을 고르고, 실행 시 오버라이드를 받는다(파생값은 다시 계산하지 않음). 타입은 S0~S2a 입력 키만 갖추고 나머지는 `Params.raw`·`Params.get("a.b.c")`로 읽는다. 지문은 `sha256`(level 포함, `meta.generated` 제외)과 `file_sha256`(파일 바이트) 두 가지다. 모델(L1/L2b) 선택은 S7에서 추가한다.
- `frames`: wxyz 쿼터니언, ZYX roll·pitch
- `signals`: Command, Measurements, TruthState, Record 필드(옛 이름 `types`)
- `engine`: SimEngine(reset, step, apply_command, measure, truth, snapshot, restore, close)
- `runner`: 영차 유지, 기록 간격
- `record`: npz + meta.json, 스냅숏(R16)
- `chrono/model`: 스텝 뒤 훅 순서를 정한다(상태 복사(R9) → 지면 부싱 R15 → 구동기 포화·$s_{ref}$ → 외력(D2, 누적기 비운 뒤 한 번) → 기록(스텝 n 동안 실제로 작용한 입력)). 모든 훅 출력은 다음 스텝부터 작용하는 1스텝 지연 규약을 따른다(R15 행, `dynamics_model.md` 4.6절)
- `verify/reference`: 전체 문자열 키 상수(R12)
- `verify/metrics`: 정착값, 문턱 교차, ERA/SSI 다출력 식별, 에너지 수지, 수렴비, 접지 시각 기구학 예측
- `verify/checks`: `CheckResult(id, item, value, ref, tol, unit, passed, ref_key)`

### 3.2 엔진 독립 인터페이스 (MuJoCo 병행 대비, Q8 미정)

- 엔진 의존 코드는 `chrono/`에만 둔다. `scenarios`, `runner`, `record`, `verify`, `sensors/imu_model`, `control`은 `SimEngine`과 `Record`만 본다.
- `Record`는 고정 이름 배열이다: `t`, `body_pos`, `body_quat_wxyz`, `body_vel`, `body_omega`, `F_cyl[4]`, `F_contact_n[4]`, `F_contact_t[4,2]`, `s_motor[4]`, `s_ref[4]`, `u_cmd[4]`, `u_applied[4]`, `bushing_anchor[4,3]`, `pad_in_contact[4]`, `F_crawler[3]`, `bushing_events`, `energy.*`.
  - `pad_in_contact`(bool)과 `F_crawler`(크롤러 접촉력 합, N)는 2026-10-20 `signals` 구현에서 더했다.
  - `energy.*`는 S4 에너지 항 7개다: `kinetic`, `gravity`, `contact_spring`, `bushing_spring`, `dissipated_viscous`, `dissipated_slip`, `motor_work`(J, S4부터 선택 필드).
  - `bushing_events`는 샘플 배열이 아닌 별도 표다: 열 `t`(s), `leg`(0~3), `kind`(1 생성, 2 소멸).
  - **좌표 규약**(TruthState·Record): `body_pos`·`body_vel`은 기체 원점의 세계 좌표, `body_omega`는 세계 좌표(자이로 모델은 켤레 쿼터니언으로 기체 좌표로 바꿔 쓴다), `F_contact_t`는 세계 x·y 성분이다. Chrono 바디 프레임이 무게중심이면 `chrono/` 쪽 진값 추출에서 기체 원점으로 바꾼다.
  - 기체 원점을 CAD 원점이 아닌 곳으로 정하면, YAML을 새 원점으로 다시 낼지 값을 쓰는 쪽에서 변환할지 그때 정한다(사용자 결정, 2026-10-20). 지금은 `frames.CadBodyTransform`만 오프셋을 적용한다.
- MuJoCo를 병행하면 같은 `SimEngine`을 구현하는 하위 패키지를 붙이고 같은 `verify/checks`를 쓴다. 지금은 구현하지 않는다.

### 3.3 제어기와의 경계

| 방향 | 내용 | 주기 |
|---|---|---|
| 관측(엔진 → 제어기) | `Measurements`: IMU(비력 3, 각속도 3; 오차 모델은 py), 압력 4(Pa, 헤드측), 스트로크 4(m; L1은 모터 위치와 보정값) | 제어 주기(기본 20 ms, 가정) |
| 명령(제어기 → 엔진) | `Command`: 다리 속도 4(m/s). 포화·스트로크 끝·210 bar 차단은 구동기 모델이 **물리 스텝마다** 한다 | 영차 유지 |
| 금지 | 제어기가 `TruthState`를 읽는 것 | runner가 막음 |

### 3.4 시험 구조와 V 판정 자동화

| 층 | 위치 | 마커 | 시간 | 내용 |
|---|---|---|---|---|
| 단위 | `05_tests/unit/` | 없음(`test_params.py`, `test_frames.py`, `test_signals.py`, `test_engine.py`, `test_reference.py`) | 각 < 1 s | 로더, 좌표, 복귀 사상·히스테리시스 수식, 기준값 키 존재, 오거 합성 |
| 엔진 규약 | `05_tests/chrono/` | `chrono` | 수 초 ~ 1분 | V0 규약, 부싱 블록 회귀, 스냅숏 왕복 |
| V 시험 | `05_tests/verify/test_S<n>_*.py` | `sim`, 긴 것은 `slow` | 수 분 ~ 수십 분 | `verify/checks`를 호출해 assert |

- 판정 실행은 `04_scripts/02_chrono/run_verify.py --stage S<n> --model L1 --level top --jobs N`이 한다. 결과는 `07_results/verify/<stage>/<run_id>/`(npz, report.json, 그림), 정착 상태는 `07_results/states/`, 요약은 `06_analysis/01_chrono/verify_<stage>_<model>.json`(git 추적)에 둔다.
- pytest와 `run_verify.py`는 같은 `checks`를 쓴다. 자동 통과/실패는 사전 점검이고 최종 판정은 dyn이 한다.
- 일상 회귀는 `pytest -m "not slow"`로 돌린다. `07_results/`는 `.gitignore`에 있다.

### 3.5 제어기 트랙 (py, 참고)

| 시점 | 내용 | 모델 |
|---|---|---|
| S3 뒤 | 개루프 명령 재생으로 runner·Record 확인 | L1 |
| S6 뒤 | IMU 오차 모델(센서 등급 우수/보통, 영점 후·출하; 장착점 캐빈 바닥 아래 상부 프레임 C1 (0.31, 0.88, 0.040) m) + 2차 필터(τ 0.5 s × 2) + **C2 제어기**(대안 C8) + 물리 기반 결합 접지 판정·탐침으로 폐루프. **±0.2°**(데드밴드 0.03°, 장착 몫 0.02° 더해 판정), $F_{min}$, 3단계. S6 제어기 검증 항목 1~8 | L1 |
| S7·S8 뒤 | 큰 경사·실 마찰·D2 재판정. 압력만 vs 결합 접지 판정 비교(S6 검증 항목 9). Chrono 접촉력을 라벨로 한 ML/DL 판정기 학습 데이터 생성($F_s$·β·경사·오거·노이즈 무작위화)과 물리 기반 판정기 비교 | L2b-NSC |
| S9 뒤 | 연약 지면 재판정 | L2b-NSC + SCM |

## 4. 실행 비용 추정

측정 근거(2026-10-19, 이 PC 28코어, pychrono 10.0.0, Δt 2×10⁻⁴ s):

| 구성 | µs/스텝 | 출처 |
|---|---|---|
| 단일 블록 SMC / SMC + 부싱 훅 / NSC PSOR 50 | 9 / 33 / 9 | `06_analysis/01_chrono/stick_friction.json` |
| 전체 규모 L1(바디 5, 모터 4, 패드 구 4, 부싱 4, SPARSE_QR; 2026-10-20부터 기본은 SPARSE_LU + 잠금, 아래 벤치마크) | 146 / **163**(4다리 훅) | scratchpad 비용 측정(물리 미검증, 2 s) |
| 전체 규모 NSC(바디 5, 힘 모터 4, PSOR 50) | 35 / **43**(힘 법칙 훅) | 같은 측정 |

계획 단가(개정 5: 용도별 dt)는 다음과 같다. L1은 **S0 실측(2026-10-20, 아래 "S0 전체 규모 스텝 비용 실측")으로 확인**했다. 패드 접지 상태 실측이 계획 단가 0.2 ms의 0.95~0.98배라 아래 단계별 합계·벽시계는 그대로 둔다(크롤러 위 구간은 과대, 아래 영향 참조). L2b-NSC는 아직 추정이다(S7에서 잼).

| 구성 | 스텝 단가 | 일반 실행 Δt 1×10⁻⁴ s | 기준해·접지 전환 Δt 1×10⁻⁵ s |
|---|---|---|---|
| L1 계획 단가 | 0.2 ms/스텝 | **시뮬레이션 1 s당 벽시계 2 s** | **1 s당 20 s** |
| L1 실측, 패드 접지(부싱 4 + 훅) | 0.190 / 0.195 ms/스텝(1×10⁻⁴ / 1×10⁻⁵ s) | **1 s당 1.9 s**(계획의 0.95배) | **1 s당 19.5 s**(0.98배) |
| L1 실측, 크롤러 정착(다리 수축, 부싱 없음) | 0.071 / 0.074 ms/스텝 | **1 s당 0.71 s**(0.35배) | **1 s당 7.4 s**(0.37배) |
| L2b-NSC(추정) | 0.06 ms/스텝(크롤러·부싱이 붙으면 2배까지) | **1 s당 0.6 s**(2배면 1.2 s) | **1 s당 6 s**(2배면 12 s) |

실측 단가는 **P코어 고정**에서 잰 값이다. 이 PC(i7-14700, P코어 8 + E코어 12)에서 창 없는 하위 프로세스를 OS 기본 배치로 두면 Windows가 E코어로 보내 **2.5배**(E코어 고정 2.7배) 느려진다. 단계별 벽시계는 실행기가 P코어 고정과 전력 제한(EcoQoS) 해제를 할 때만 성립한다(`step_cost_S0.py` `place_process`; S6 runner에 넣을 것, 6절 #24). 4병렬(`--jobs 4`)은 P코어 8개 안이라 단가가 같을 것으로 본다(병렬 실행은 재지 않았다). 9병렬 이상은 하이퍼스레드 공유나 E코어 사용으로 단가가 오른다.

- 아래 표의 "합계"는 **Δt 1×10⁻⁴ s 환산 시뮬레이션 길이**다. Δt/2, Δt/4 실행은 2배, 4배로, 1×10⁻⁵ s 구간은 10배로, 2Δt는 절반으로 센다. 벽시계는 L1이면 합계 × 2, NSC면 × 0.6(2배면 × 1.2)이다.
- 접지 전환 창(이 계획의 가정): V4는 첫 접지 0.1 s 전 ~ 마지막 정지 0.3 s 뒤(약 14.9~18.0 s, 3.1 s), 다리 부상으로 끝나는 연속 신장(V6, V14 RL+, V15(a))은 부상 전후 2 s, S2b 이벤트 시험은 사건 3개 × 1 s, D2 외란은 하중 피크 5 s(크기·시간 미정)를 1×10⁻⁵ s로 돈다. 나머지 구간은 1×10⁻⁴ s다.
- V9 기준해(1×10⁻⁵ s)는 전 구간을 같은 Δt로 돈다(수렴비 비교용).
- 크롤러 구 배열과 SCM은 포함하지 않았다. 크롤러 D안은 S0 실측(아래)에 들어 있다. SCM은 S9에서 잰다.
- 솔버 비교(2026-10-20, 5바디 L1: 상부체 + 다리 이동부 4 + 위치 모터 4 + 패드 구 4, Δt 1×10⁻⁴ s, 1 s): SPARSE_QR **91 µs/스텝**, SPARSE_LU 141 µs, PARDISO_MKL 300~415 µs(스레드 수·희소 패턴 잠금 변형, 결과 차 ≤ 1×10⁻⁹ N). 이 규모에서는 Pardiso로 비용을 줄일 수 없다. (이 5바디 측정은 아래 전체 규모 벤치마크로 대체됐고, L1 기본 솔버는 2026-10-20에 SPARSE_LU + 잠금으로 바뀌었다.)

**선형 솔버 벤치마크(2026-10-20, 요약 `06_analysis/01_chrono/solver_benchmark.json`, 그림 `solver_benchmark.png`, 모습 `solver_benchmark_{L1,SCM,scale}.gif`)**. 이 PC, pychrono 10.0.0, 사례마다 별도 프로세스, 예열 뒤 3구간 벽시계 중앙값(µs/스텝). LS = Chrono `GetTimerLSsetup + GetTimerLSsolve`(행렬 조립 + 분해 + 풀이). "잠금" = `LockSparsityPattern(True)`. 결과 일치는 같은 예열 스텝 뒤 상태량 최대 차. 이 측정은 S0 정식 비용 측정(체크리스트 항목)이 아니다.

재생성(스크립트 `04_scripts/02_chrono/solver_benchmark/`, 개별 결과 `07_results/solver_benchmark/`): GIF만 `python -I -u 04_scripts/02_chrono/solver_benchmark/make_gifs.py all`(저장된 결과 사용, 약 5분), 요약 JSON·PNG만 `python -I 04_scripts/02_chrono/solver_benchmark/summarize.py`, 전체 재측정 + 요약 + GIF `python -I -u 04_scripts/02_chrono/solver_benchmark/run_benchmark.py all --report`(약 50분, 그중 N = 500 SPARSE_QR 두 건이 약 27분). `python`은 `Chrono-dev` 인터프리터다.

| 모델 | KKT 미지수 | SPARSE_QR | SPARSE_LU | PARDISO_MKL | 결과 일치 |
|---|---|---|---|---|---|
| 전체 규모 L1(바디 5, 모터 4, 패드 구 4, 크롤러 구 18(측정 당시 2×9, 접촉 없음; D안은 24개 — 접촉 없는 구는 광역 탐색 비용만 늘어 S0 재측정에서 확인), 지면 부싱 4 + Python 훅), Δt 1×10⁻⁴ s, 잠금 끔 | 54 | 176 (LS 89) | 162 (LS 75) | 540 (LS 419) | 위치 ≤ 1.3×10⁻¹⁵ m, 패드 힘 ≤ 1.2×10⁻⁷ N |
| 같은 모델, 잠금 켬 | 54 | 147 (LS 63) | **133 (LS 46)** | 447 (LS 356) | 같음 |
| 같은 모델, Δt 1×10⁻⁵ s, 잠금 켬 | 54 | 147 | **134** | 438 | 같음 |
| SCM 패드 4 + 크롤러 띠 활성 영역, 격자 5 cm(광선 1,872/스텝), 잠금 켬 | 54 | 575 (LS 65) | 566 (LS 53) | 807 (LS 281) | 위치 ≤ 4.4×10⁻¹⁶ m |
| SCM 격자 2 cm(광선 11,800) | 54 | 3,146 (LS 75) | 3,085 (LS 68) | 3,373 (LS 314) | 같음 |
| SCM 격자 1 cm(광선 47,179) | 54 | 12,835 (LS 84) | 12,716 (LS 79) | 13,179 (LS 371) | 같음 |
| 합성 격자 N = 5 / 20 / 50 / 100 / 200 / 500(부싱 결합), 잠금 켬 | 45 ~ 4,500 | 108 / 1,214 / 8,167 / 48,588 / 406,912 / 시간 초과(> 900 s) | **101 / 636 / 1,854 / 4,205 / 9,083 / 25,543** | 353 / 1,182 / 2,940 / 6,554 / 15,570 / 39,415 | z ≤ 1×10⁻¹⁴ m |
| 합성 체인 N = 5 … 500(구면 조인트 결합), 잠금 켬 | 45 ~ 4,500 | 96 / 570 / 3,536 / 21,004 / 147,681 / 3,961,340 | **93 / 372 / 919 / 1,838 / 3,685 / 9,703** | 277 / 641 / 1,432 / 2,635 / 5,607 / 14,567 | z ≤ 1.3×10⁻¹⁴ m |

- 전체 규모 L1에서는 SPARSE_LU + 잠금이 가장 빠르다(133 µs, 이전 기본 QR 잠금 끔 176 µs 대비 −24 %). 잠금은 행렬 조립을 31 → 4.5 µs로 줄인다. 1×10⁻⁵ s에서도 스텝 단가는 같아 4절 계획 단가(0.2 ms/스텝)는 그대로 유효하다. 벽시계와 Chrono 스텝 타이머 차 약 25 µs가 Python 부싱 훅이다. 크롤러 구는 수평 정착 상태에서 바닥과 떨어져 있어 접촉 비용이 없다(Bullet 광역 탐색만, 충돌 타이머 약 3.5 µs).
- PARDISO_MKL은 KKT 4,500까지 어느 모델에서도 SPARSE_LU보다 느리다(스텝 1.5~3.5배, LS 2.1~8.2배). 54 미지수에서도 분해 호출에 약 350 µs가 들어 호출당 고정 비용이 크다. `MKL_NUM_THREADS` 1과 기본값의 차는 잡음 수준이다. 전체 규모 L1의 Pardiso는 반복 간 편차가 40~50 %로 크다.
- SPARSE_QR은 크기에 대해 초선형으로 늘어 KKT 180(N = 20)에서 Pardiso와 비슷해지고, 450 이상에서는 Pardiso보다 2.5~270배 느리다. KKT 45에서는 QR ≈ LU다.
- SCM 비용은 거의 전부 SCM 광선 질의다(`GetTimerSetup` 기준 5 cm 약 500 µs, 2 cm 약 3.0 ms, 1 cm 약 12.7 ms, 광선당 약 0.27 µs). LS 몫은 1 % 안팎이라 솔버 선택이 SCM 비용을 바꾸지 못한다. 광선 수는 활성 영역 면적 / 격자² 이고, 지금 영역의 약 70 %가 크롤러 띠(4.1 m × 0.4 m × 2)다. SCM 토양 값은 **시험용 가정**(Wong 표 '중점토 25 %', n 0.13; Janosi 0.01 m, K 2×10⁸ Pa/m, R 3×10⁴ Pa·s/m는 Chrono 예제 수준)이며, 이 값에서 전방 패드는 3 s에 76 mm 침하하고 크롤러 앞부분이 토양에 닿았다(22.7 kN).
- 모델 규모별 권장: ① 지금 L1 전체 규모(KKT 약 54) → SPARSE_LU + 잠금(QR 잠금 켬과 차 약 9 %, 결과 동일). ② L2b-NSC는 PSOR(반복) 그대로, 직접 솔버 비교 대상이 아니다. ③ SCM 단계 → 솔버는 무관(LU + 잠금), 격자 크기와 활성 영역이 비용을 정한다(2 cm, 현재 영역이면 Δt 1×10⁻⁴ s에서 시뮬레이션 1 s당 약 31 s). ④ KKT 180 이상의 큰 모델 → SPARSE_LU. QR은 쓰지 않는다. Pardiso는 이 Chrono 빌드에서 KKT 4,500까지 이점이 없다.
- **R11 기본 솔버 변경(반영됨, 사용자 결정 2026-10-20)**: L1 기본을 SPARSE_QR에서 **SPARSE_LU + `LockSparsityPattern(True)`**로 바꿨다. `make_system()`(`chrono/system.py`), R11, S0 체크리스트 메모를 함께 고쳤다. SPARSE_QR·PARDISO_MKL과 잠금 끔은 옵션으로 남겼다. 잠금 상태의 구조 변경 처리는 S0 체크리스트 `make_system()` 메모를 본다.

**S0 전체 규모 스텝 비용 실측(2026-10-20, S0 체크리스트 항목)**. 요약 `06_analysis/01_chrono/step_cost_S0.json`, 사례별 결과 `07_results/step_cost_S0/`. 재생성: `python -I -u 04_scripts/02_chrono/solver_benchmark/step_cost_S0.py run`(9사례 약 4분, `python`은 `Chrono-dev`).
- 조건: Intel i7-14700(논리 28), pychrono 10.0.0(projectchrono py312h418371c_1198), 사례마다 별도 프로세스, **P코어 고정 + EcoQoS 해제**. 오거 top. 모델: 상부체 + 다리 이동부 4(위치 모터 4, 상수 0) + 패드 구 4 + 크롤러 D안 구 24 + 바닥 1×10⁹ kg(패드 패치 4, 크롤러 띠 패치 2 — 재질 합성이 섞이지 않게 분리) + `GroundBushingCoulomb`(스텝마다 `after_step`). 바디 6(바닥 포함), 링크 4, 기타 항목 4(부싱 컨테이너; 크롤러 상태 0), 속도 좌표 30, 구속 24, KKT 54. 접촉 수 패드 상태 4, 크롤러 상태 10~16.
- 두 상태: **패드 접지**(운용 신장, 크롤러 50 mm 위, 정적 침투만큼 내려 시작, t = 0 부싱 부착) / **크롤러 정착**(다리 수축, 패드 공중, 부싱 없음, 정적 침투만큼 내려 시작). 예열(1×10⁻⁴ s 0.5 s, 1×10⁻⁵ s 0.2 s) 뒤 1 s 구간을 1×10⁻⁴ s 5회, 1×10⁻⁵ s 3회 쟀다(스텝마다 `DoStepDynamics`와 훅을 따로 계시). 벽시계는 계시 없는 1 s 구간 값이다. 모든 사례에서 R15 이벤트 0, 끝 시점 수직력 합/중량 0.99~1.01(물리 판정은 아님).

| 상태, Δt, 솔버 | 스텝 중앙값 (p5 / p95) µs | 벽시계 µs/스텝 | 1 s당 벽시계 | 훅 평균 µs (비중) | 계획 0.2 ms 대비 |
|---|---|---|---|---|---|
| 패드 접지, 1×10⁻⁴ s, LU+잠금 | 181 (177 / 236) | 190(반복 실행 194) | 1.9 s | 81 (43 %) | 0.95배 |
| 패드 접지, 1×10⁻⁵ s, LU+잠금 | 182 (176 / 244) | 195 | 19.5 s | 82 (43 %) | 0.98배 |
| 크롤러 정착, 1×10⁻⁴ s, LU+잠금 | 68 (65 / 84) | 71 | 0.71 s | 13 (18 %) | 0.35배 |
| 크롤러 정착, 1×10⁻⁵ s, LU+잠금 | 70 (66 / 90) | 74 | 7.4 s | 14 (18 %) | 0.37배 |
| 패드 접지, 1×10⁻⁴ s, QR+잠금(참고) | 200 (193 / 276) | 211 | 2.1 s | 83 (40 %) | 1.05배 |
| 패드 접지, 1×10⁻⁴ s, LU, 부싱·훅 없음(분해용, 유효 모델 아님) | 49 (47 / 59) | 51 | 0.51 s | — | 0.25배 |
| 패드 접지, 1×10⁻⁴ s, LU, OS 기본 배치 | 430 (177 / 681) | 479 | 4.8 s | 237 | 2.4배 |
| 패드 접지, 1×10⁻⁴ s, LU, E코어 고정 | 429 (419 / 678) | 510 | 5.1 s | 284 | 2.5배 |

- **비용 분해(패드 접지, 1×10⁻⁴ s, 190 µs)**: Chrono 스텝 104 µs(선형 솔버 LSsetup+LSsolve 48, 그중 LU 분해 42·조립 4.6; 충돌 3.9; **지면 부싱 하중 4개 약 55** — 부싱이 없으면 Chrono 스텝 49 µs) + **Python 훅 81 µs** + 루프 약 4.5 µs. 지면 부싱 몫이 합쳐서 약 136 µs(72 %)다. 크롤러 상태는 Chrono 57 µs(LS 43, 충돌 7.6~9.7 µs — 접촉 10~16개) + 훅 13 µs(부싱 없는 경로)다.
- **이전 측정과 차이**: Chrono 스텝은 솔버 벤치마크(133 µs 중 훅 약 25 µs → Chrono 약 108 µs)와 같다. 크롤러 구 18 → 24개는 충돌 3.5 → 3.9 µs로 차이가 없다(패드 상태, 크롤러 비접촉). 총 133 → 190 µs(1.42배)는 훅 비용 25 → 81 µs(3.2배) 때문이다. 벤치마크 훅은 블록 시험 `hook()`을 그대로 옮긴 것이고, `GroundBushingCoulomb.after_step`은 R15·기울어진 바닥·복사 규약(R9) 때문에 Chrono 벡터 변환이 스텝당 약 34회, `normal_world()` 5회, `np.linalg.norm` 8회, 미끄럼이 없을 때도 매 스텝 `SetDamping`을 부른다(cProfile). 4절 측정 근거(163 µs, QR, Δt 2×10⁻⁴ s) 대비 1.16~1.20배다.
- **Δt 영향**: 스텝 단가는 Δt와 거의 무관하다(1×10⁻⁵ / 1×10⁻⁴ s: 패드 1.03배, 크롤러 1.05배). 벽시계는 스텝 수에 비례한다.
- **단계 재추정 영향(P코어 기준)**: 패드 접지 구간은 계획대로(0.95~0.98배). 크롤러 위 구간은 계획 단가의 약 0.36배라 과대 추정이었다. 예: S2b 크롤러 위 정착 3 × 65.5 s = 139 s(계획 393 s). V4 판정 실행(전환 창만 1×10⁻⁵ s) 약 99 s(계획 121 s). **V9 V4 기준해(1×10⁻⁵ s 전 구간) 약 457 s = 7.6분**(접지 전 15.0 s 크롤러 상태 + 17.7 s 패드 상태; 계획 654 s). 단일 실행 10분 기준 아래로 내려오지만 여유가 작고 OS 기본 배치면 약 19분이라, 메인 세션 권고 대상으로 그대로 둔다. 위 단계 표의 합계·벽시계는 바꾸지 않았다(보수적).
- **병목과 줄일 곳**: ① Python 훅(81 µs, 43 %): 다리마다 반복하는 `normal_world()`·바닥 변환을 스텝당 한 번으로, Chrono 벡터 생성 줄이기, 값이 바뀔 때만 `SetDamping`. 결과를 바꾸지 않는 최적화라 S0 회귀(블록 3건·히스테리시스·스냅숏)로 확인할 수 있다. ② Chrono 부싱 하중(55 µs, 29 %): `ChLoadBodyBodyBushingSpherical`의 강성·감쇠 행렬 계산 몫으로 본다(부싱 4개 제거 시 사라짐; 내부 구현은 확인하지 않았다). ③ LU 분해(42 µs, 22 %): KKT 54에서 고정 비용, 솔버 선택으로는 더 줄지 않는다(QR +11 %). ④ 충돌(4~10 µs)은 작다.

| 단계 | 주요 사례(시뮬레이션 길이) | 합계(Δt 1×10⁻⁴ s 환산) | 예상 벽시계 직렬 / 4병렬 | 장시간 |
|---|---|---|---|---|
| S0 | 블록 회귀·히스테리시스·스냅숏(블록 회귀는 기준 파일과 같은 2×10⁻⁴ s, 단일 블록이라 몇 초). 전체 규모 비용 측정 2 s × {1×10⁻⁴, 1×10⁻⁵ s} × {L1, NSC} | 약 30 s + 측정 8 s | 약 1.5분(측정 1×10⁻⁵ s 몫 약 52 s). **실측(2026-10-20)**: L1 비용 측정 9사례(패드·크롤러 × 2 Δt, QR, 반복, 배치 2, 분해 1) 약 4분, NSC 미측정(S7) | 아니오 |
| S1 | 3단계 × (정적해 초기화 + 정착 10 s + 정지 5 s) = 45 s, 초기화 없는 교차 1건 53 + 5 = 58 s. 초기화가 안 되면 3 × 58 s = 174 s | 103~174 s | 3.5~6분 | 아니오 |
| S2a | V7 진단 roll·pitch 2 × 20 s(+ 진단 ⑤ yaw 2 s), V12 3 × (램프 3 s + 정착 53 s + 평균 3 s) | 약 217~219 s | 7분 | 아니오 |
| S2b | V0 2 s, V11 35 s(공중 다리, 접촉 없음), 이벤트 시험 20 s(전환 3 s × 10 → 47 s), 크롤러 위 정착 3단계 × 65.5 s ≈ 197 s(개정 6 D안; 해석해 초기화면 0) | 약 281 s(초기화면 약 84 s) | 9.5분(3분) | 아니오 |
| S3 | V8(a) 60 s(Δt) + 60 s(2Δt → 30 s) = 90 s. V4(저장된 크롤러 정착 상태에서 모터 출발 → 마지막 정지 17.7 s + 정착 15 s = 32.7 s, 전환 창 3.1 s × 10 → 60.6 s) × (기준 + 감속 램프 감도) = 121 s. V5 +1 / +5 mm 32 s. V6 FL+·FL− 2 × (150 s, 부상 창 2 s × 10 → 168 s) = 336 s. V9 매끄러운 시험(① V5 +1 mm 12 s + ② 자유 진동 5 s) × (2 + 4 + **10**) = 272 s. V9 V4 차 32.7 s × (1 + 2 + 4 + **10**) = 556 s | 약 1,407 s | 47분 / 약 12~13분 | 예. **V9 V4 기준해 1건(1×10⁻⁵ s 전 구간)이 약 654 s(11분)라 단일 실행 10분을 넘는다 → 메인 세션 권고** |
| S4 | V7 초기 속도 6종(2 × 20 s + 4 × 2 s) 48 s. V8(b) 30 s. β 3값 × (정적 15 s + V5 32 s + 진동수 48 s) = 285 s. V6 1.6 GPa만(문턱 약 8 mm, 약 100 s, 부상 창 → 118 s). 로드측 감도(선택) 50 s | 약 531 s | 18분 / 약 5분 | 직렬은 예 |
| S5 | 3단계 × (V1 15 s + roll·pitch 2 × 20 s) | 약 165 s | 5.5분 | 아니오 |
| S6 | V11b 단일 다리 20 s, 센서 20 s, V17 경로 15 s, 폐루프 연기 60 s | 약 115 s | 4분 | 아니오 |
| S7(NSC) | S1~S5의 top 시험 재실행(β 제외: S1 73 s + S2a 217 s + S2b 150 s(개정 6) + S3 1,407 s + S4 128 s + S5 55 s) 약 2,029 s, V14 3경우 × (V12 59 s + RL+ 민감도 32 s + RL+ 연속 신장 부상까지 최대 약 175 s(부상 창 → 193 s) + 로킹 40 s) = 972 s | 약 3,001 s | 30분(단가 2배면 60분) / 7.5~15분 | 직렬은 예 |
| S8 | NSC: V15(a) 4 × 부상까지(약 13~14 mm, 0.1 mm/s, 부상 창 포함) ≈ 617 s, V15(b) 4 × 200 s = 800 s, 관성 확인(0.05 mm/s, 12 kN, 부상 창 포함) 278 s, D2 3단계 × 2 로크 밸브 × 30 s(피크 창 5 s × 10 → 75 s) = 450 s, ζ 감도(0.01, 0.10) 2 × 3 × 75 s = 450 s → 약 2,595 s(0.6 s/s). L1 V17 3 × 75 s = 225 s(2 s/s) | 약 2,820 s | 33.5~59.5분 / 8.5~15분 | 직렬은 예 |
| S9 | SCM 미측정(1~10 ms/스텝 가정 시 Δt 1×10⁻⁴ s로 정착 53 s 1건에 약 9~88분). 2026-10-20 벤치마크(시험용 토양, 패드 4 + 크롤러 띠 영역): 5 / 2 / 1 cm 격자에서 0.57 / 3.1 / 12.7 ms/스텝 → 정착 53 s 1건 약 5 / 27 / 112분 | — | 미정 | 예 |

기준해·접지 전환 1×10⁻⁵ s 실행 비용(위 표에 포함된 것을 따로 모음):

| 실행 | 시뮬레이션 길이 | L1 벽시계 | L2b-NSC 벽시계(단가 2배) | 비고 |
|---|---|---|---|---|
| V9 V4 기준해(전 구간 1×10⁻⁵ s) | 32.7 s | **654 s(10.9분)**; S0 실측 단가로 약 457 s(7.6분, P코어 고정; OS 기본 배치면 약 2.5배) | 196 s(392 s) | L1은 계획 단가로 단일 실행 10분 초과 → 메인 세션 권고(실측으로도 여유가 작아 유지) |
| V9 매끄러운 시험 기준해(① 12 s + ② 5 s) | 17 s | 340 s | 102 s(204 s) | |
| V4 판정 실행(전환 창 3.1 s만 1×10⁻⁵ s) | 32.7 s | 121 s(전 구간 1×10⁻⁵ s로 돌리면 654 s) | 36 s(73 s) | 기준 + 감속 램프 감도 2건 |
| 부상으로 끝나는 연속 신장(창 2 s) | 사례당 2 s 창 | 사례당 +36 s | 사례당 +11 s(+22 s) | V6, V14 RL+, V15(a), 관성 확인 |
| D2 외란 피크(창 5 s, 가정) | 사례당 5 s 창 | 사례당 +90 s | 사례당 +27 s(+54 s) | D2 크기·시간 결정 뒤 창을 다시 정함 |

장시간 규칙:
- 한 번의 실행이 10분을 넘을 것 같으면 에이전트가 직접 띄우지 않는다. `run_verify.py`의 명령 전체·예상 시간·출력 경로를 **메인 세션 권고**로 넘긴다. 지금 추정으로는 **S3 V9 V4 기준해(L1, 1×10⁻⁵ s 전 구간, 약 11분)**가 여기에 든다.
- 직렬 합계가 30분을 넘는 단계(S3, S7, S8)는 메인 세션이 long-running-task-monitor 규칙을 따른다.
- S3·S4·S7·S8은 `--jobs 4`로 병렬로 돌린다(4병렬이면 5~15분). S9는 비용을 잰 뒤 정한다.

## 5. 미정 사항과 결정 시점

| 항목 | 필요한 단계 | 결정 시점 | 미정이면 |
|---|---|---|---|
| 기체 좌표 원점 | S0 | **결정됨**(2026-10-20 사용자 결정): CAD 원점 유지 = 선회 링 볼트원 PCD 1,120 mm 중심축 ∩ 데크 하면(`00_docs/00_cad/cad_origin_mass_imu.md` 1절) | — |
| 크롤러 YAML 키 반영(`contact.crawler.*` D안, `simulation.settle_on_*`) | S2b, S3 | **반영됨**(2026-10-20, D안 사용자 결정, `export_params.py`) | — |
| 지면 경사 시험 범위 | S2a, S7 | S2a 전 | V12 3경우 |
| Δt 확정 | S4 이후 | **용도별 결정됨**(2026-10-20 사용자 결정, YAML 반영): 일반 실행 L1·L2b-NSC 1×10⁻⁴ s(`simulation.L1.dt_s`, `simulation.L2b_NSC.dt_s`; 옛 로킹 수치 감쇠 규칙 상한 1.386×10⁻⁴ s. 개정 7: 모드별 규칙 상한은 2.05×10⁻⁴ s(3차)이고 2×10⁻⁴ s 복귀는 S3 V8(a) 뒤 사용자에게 다시 묻는다, S3 위험 ①-2), 기준해·접지 전환 해석 1×10⁻⁵ s(`simulation.dt_reference_s`, `simulation.dt_transition_s`). S3 V8(a)·V9로 확인(dyn) | 규칙값으로 진행. V8(a) 실패 시 dyn과 협의(S3 위험 ①) |
| MuJoCo 역할(Q8) | 병행 시 S1~S4 재사용 | **S4 끝 전** | 인터페이스만 |
| 자세 정확도 목표 | S6 뒤 폐루프 | **결정됨**(2026-10-20): ±0.2°, 데드밴드 0.03°, IMU 현장 영점 교정 의무 | — |
| IMU 장착 위치(Q4) | S6 | **결정됨**(2026-10-20): 캐빈 바닥 아래 상부 프레임. 좌표 (0.31, 0.88, 0.040) m(C1, BASE DECK 좌측 폰툰 15 mm 가로판 윗면, 후보 C1, 2026-10-20 사용자 결정). 실기 설치 때 확인 | — |
| 자세 신호 필터 | S6 뒤 폐루프 | **결정됨**(2026-10-20): 2차 저역통과(1차 τ 0.5 s × 2단) | — |
| 센서 모델 선정(노이즈·바이어스·지연 사양), 제어 주기 | S6 | **S6 전** | 가정치(영점 오차 허용 ≤ 2.44 mg = 0.14°(장착 몫 0.02°, 2026-10-20 결정; 이전 2.27 mg = 0.13°), ±0.2° 캐빈·데드밴드 0.03° 예산; 등급 4종으로 감도. 20 ms) |
| 제어기 구조(D1) | S6 뒤 폐루프 | **잠정 결정**(2026-10-20): C2, 대안 C8. 접지 판정은 물리 기반 결합 판정 + 탐침, ML/DL은 비교 후보 | — |
| 제어기 세부(탐침 빈도, 비틀림 목표, 게인), roll·pitch 목표 범위 | S6 뒤 폐루프 | **S6 끝 전** | `control_candidates_comparison.md` 7.1절 값 |
| D2 외력 크기·작용 시간·작용점(Q9) | S8 | **S7 시작 전**(늦어도 S8 전) | 정착 상태 지표만 |
| 카운터 밸런스 교체(Q10), 실 마찰 크기 | S8 | 막지 않음 | 두 옵션 구현, 감도 0/2/5/12 kN |
| 감쇠 ζ(Q6) | S1~S8 | **결정됨**(2026-10-20, [damping_survey.md](../01_dynamics/damping_survey.md), 문헌 추론값): 다리 축 0.03(잠김, heave 7.39 Hz 기준, 감도 0.01~0.10), 이동 중 0.10, 크롤러 콘크리트 0.05 / 토양 0.2(감도 0.02~0.3), 구조·마스트 0.015 | — |
| SCM 파라미터 | S9 | **S9 전** | S9 보류 |
| 마스트 굽힘(Q4) | S6, S8 | 자료가 오면 | 강체 |
| 실제 운용 중량 | 전부 | 언제든 | 경우 C 유지(2026-10-20 사용자 결정, 질량 감사 `cad_origin_mass_imu.md` 2절). 바뀌면 YAML 재생성 → dyn `run_reference.py` → 저장 상태 폐기(sha256 불일치) → V 회귀 |

## 6. 위험 목록과 대응

| # | 위험 | 단계 | 대응 |
|---|---|---|---|
| 1 | SMC 재질 합성식 미확인(패드 전·후, 크롤러) | S1, S2b | 다리별·크롤러 바닥 패치 + 같은 재질(R13), V2로 실제 $k_n$ 역산 |
| 2 | `GetContactForce()` 프레임 미확인, NSC 반력 환산 | S1, S7 | 단위 시험, `ReportContactCallback` 교차, V1 |
| 3 | 모터 Z축·반력 부호 | S2b | V0(R4) |
| 4 | 감쇠 규약 위반 | 전부 | V0 자동 검사, V7 진단 규칙 |
| 5 | 중력 기본 0, 충돌 시스템 누락 | 전부 | `make_system()` 한 곳 |
| 6 | `GetPos()` 참조 저장 | 전부 | `probes`만 읽고 즉시 복사 |
| 7 | 정착 과도가 길어(τ 11.5 s) 정적·정지 판정이 흐려짐 | S1~S5 | 해석 정적해 초기화, 안 되면 ≥ 53 s, 정착 상태 저장·재사용(R16) |
| 8 | 크롤러 접촉이 접지 시각을 바꿈(D안 정착 자세 $u_z$ −3.19 mm, pitch +0.170°). 접지 순서는 크롤러 총 강성 가정에 따라 뒤집힌다(×1 전방 먼저, ×3 후방 먼저) | S3 | 크롤러 정착 자세 초기화(안 되면 ≥ 65.5 s), **다리별 접지 시각을 같은 배치·강성의 기준해와 ±0.05 s로** 비교(D ×1 / ×3 / NSC 강체 극한 기준해가 따로 있음). 순서는 판정하지 않음 |
| 9 | 부상·재접지 chatter, $N<0$ | S2b, S3, S8 | R15($\max(N,0)$, 히스테리시스, 횟수 기록) |
| 10 | 크롤러 접촉점 수 변동(끝 슈 구가 틈이 닫힐 때만 닿음) | S2b, S3 | D안 구 24개(R13), 단방향 끝 슈 구는 틈만큼 위에 둔다. 정착 활성 구 14개를 V0로 확인. YAML 키는 반영됨 |
| 11 | 충돌 쌍 오접촉(로드–상부체, 크롤러–로드) | S1 | 충돌 패밀리(R14), V13 |
| 12 | 수치 감쇠(또는 음의 수치 감쇠)를 Δt 확정 뒤에 발견 | S3 | V8(a)를 V9 앞에, 60 s, Δt 비례 확인 |
| 13 | 사건이 섞인 시험으로 차수를 재면 무의미 | S3 | 차수는 매끄러운 시험에서, V4는 차만 |
| 14 | 가까운 모드(5.8~8.0 Hz) 분리 실패 | S4, S7 | 초기 속도 가진 + 모드 투영(`mode_shapes_rev5`), 창 길이 분리, ERA/SSI 교차. 강성을 바꾼 실행(β 감도)에는 Φ를 쓰지 않음 |
| 15 | 힘 포화를 제어 주기로 판정하면 9.4 kN 초과 | S6 | 물리 스텝마다 판정 |
| 16 | 단일 다리 강체 묶음은 힘이 부정, 인장 불가 | S6 | 양방향 스프링 $k_n$ |
| 17 | L2b 가이드 x·y 해제 API | S7 | FREE + `ChLinkLockAlign` 대안 |
| 18 | L2b 힘 법칙 양해 갱신 | S7 | 필요 시 `ChLinkTSDA` |
| 19 | PSOR 반복 오차 | S7 | 반복 수 증가 + 비용 재측정 |
| 20 | NSC 인공 모드(배열 뒤 4개)를 기준으로 착각 | S7 | 앞 6개만 |
| 21 | 기준값 키 약기로 상수 오류 | 전부 | 전체 문자열 상수 + 키 존재 시험(R12) |
| 22 | 기준값 출처가 여러 파일(`reference.json`, `actuator_L2_feasibility.json`, YAML)로 나뉨 | 전부 | `verify/reference`가 파일별 sha256과 전체 문자열 키를 함께 관리. 기존 `C_seal_friction` 0 → 16 → 0 mm `runs`는 V15에 쓰지 않음(양방향 접촉) |
| 22a | **실 마찰 $F_s$ 12 kN에서 압력 판정이 부상을 놓친다**(V15(a) 기준해: 압력이 $F_{min}$에 닿기 전에 RL이 뜨고, 부상 순간 RL 압력 판독은 약 10.94 kN으로 $F_{min}$ 9.453 kN보다 높다) | S8, 제어기 트랙 | 모델 오류가 아니라 판정 결과로 보고한다. 제어기(py)·dyn에 전달: 압력 기준 $F_{min}$ 판정만으로는 $F_s$가 수 kN을 넘으면 접지 유지를 보장하지 못한다 → $F_{min}$ 마진에 $F_s$ 크기를 더하거나 다른 판정(스트로크·자세 일관성)을 함께 써야 한다. S8 결과로 Chrono에서 재현되는지 확인 |
| 23 | YAML·reference 판 불일치, 낡은 정착 상태 재사용 | 전부 | meta와 스냅숏에 sha256, 불일치 시 복원 거부 |
| 24 | Python 훅 비용 | S3 이후 | 4다리 벡터화, 사례 병렬. Pardiso는 5바디에서 QR보다 3배 이상 느려 비용 절감 수단이 아니다(S0 비용 측정에서 전체 규모로 재확인). **S0 실측(2026-10-20)**: `GroundBushingCoulomb.after_step` 81 µs/스텝 = 패드 접지 스텝의 43 %, Chrono 부싱 하중 55 µs와 합치면 72 %(4절 S0 실측). 결과를 바꾸지 않는 훅 최적화(변환 재사용, `SetDamping`은 바뀔 때만) 후 S0 회귀로 확인. **하이브리드 CPU 배치**: OS 기본 배치는 E코어로 가 2.5배 느려지므로 P코어 고정 + EcoQoS 해제를 한다 — **구현됨(S1, `03_src/outrigger_sim/hostcpu.py`, `run_S1.py`가 사용, `result.json` `timing.cpu_placement` 기록)**. S6 runner도 이 모듈을 쓴다 |
| 25 | 부싱 감쇠 2배·SMC 질량당 감쇠의 버전 의존 | 전부 | S0 회귀가 버전 변경을 잡음 |
| 26 | SCM 비용·격자·침하 | S9 | 단일 패드 측정 먼저 |

## 7. 이 계획의 가정

| 가정 | 값 | 비고 |
|---|---|---|
| 스텝 단가 | L1 0.2 ms, L2b-NSC 0.06 ms(2배까지) | 전체 규모 측정 + 센서·기록 몫. **L1은 S0 실측으로 확인(2026-10-20)**: 패드 접지 0.190~0.195 ms, 크롤러 정착 0.071~0.074 ms(P코어 고정, 센서·기록 몫 제외). L2b-NSC는 S7에서 잼 |
| 제어 주기 | 20 ms | `dynamics_model.md` 6.2 상한 |
| 정착 길이(해석 정적해 없음) | 패드 위 ≥ 53 s, 크롤러 위 ≥ 65.5 s(개정 6 D안; 이전 2×9 23.2 s) | $\tau\ln100$. τ = 11.5 s(1차 로킹, ζ 0.00777) / 14.2 s(D안 크롤러 위 pitch 1.327 Hz, ζ 0.0084). `dynamics_model.md` 개정 8 4.5절 1 |
| 중력 램프 | 3 s(2~5 s 범위) | 1차 주기 0.56 s의 4배 이상 |
| 부상·재접지 판정 | **$t_{lift}$ = 1 ms(시간 기준, 사용자 결정 2026-10-20)**: Δt 1×10⁻⁴ s에서 10스텝, 1×10⁻⁵ s에서 100스텝($n_{lift}=\lceil t_{lift}/\Delta t\rceil$). $N_{th}$ = 100 N | R15. 판정이 Δt와 무관해야 V9 수렴 비교가 성립한다. 값(1 ms, 100 N)은 S2b 이벤트 시험으로 조정 |
| 크롤러 형상 | D안: 트랙 2개 × (롤러 위치 구 6개 + 틈 있는 끝 슈 구 6개) = 24개(개정 6, YAML `contact.crawler.sphere_layout.*`) | 접촉점 위치 고정, 끝 슈는 단방향. 가정 값은 `dynamics_model.md` 3.8절 소관 |
| 바닥 패치 | 다리별 4개 + 크롤러 1개 | 합성식 미확인 대응 |
| V4 시작점 | 크롤러 위 정착 상태, 다리 0 m, t = 0 모터 출발 | 개정 5 절차(기준해 시각 원점과 같음) |
| V15 관성 확인 | 0.05 mm/s 1건 | 기준해의 로드 무질량 가정 확인 |
| 사례 병렬 | 프로세스 4개 | 28코어에서 늘릴 수 있음 |
