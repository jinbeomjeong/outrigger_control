# Chrono 모델 단계별 구축 계획 (2026-10-19, 개정 3: 2026-10-20)

작성: cad-expert. **계획 문서다.** 패키지 뼈대(3.1절 "있음")만 만들어져 있고 모델 코드는 아직 없다.

개정 3(2026-10-20): 사용자 결정(CLAUDE.md 2026-10-20 기록)을 반영했다. 근거는 [imu_cabin_and_accuracy_review.md](imu_cabin_and_accuracy_review.md) 5.2절 표(개정 2 기준 513·338·559행 지적)와 [control_candidates_comparison.md](control_candidates_comparison.md) 7.3절이다.
- 자세 정확도 목표를 ±0.1°에서 **±0.2°**로 바꿨다. 완료 판정 데드밴드 0.03°는 유지한다. IMU 현장 영점 교정은 운용 절차로 의무다. 센서 정지 영점 오차 허용은 0.13°(2.27 mg)다(캐빈 장착 몫 0.03° 포함 예산).
- IMU 장착점: **캐빈 바닥 아래 상부 프레임**, 기체 좌표 약 (0.20, 0.88, 0.30) m(좌표는 가정). 로킹 순간 회전 중심이 지면 아래라 높게 달수록 겉보기 기울기 증폭이 커진다.
- 자세 신호 필터: 2차 저역통과(1차 τ 0.5 s × 2단).
- 제어 구조: C2 잠정 확정, 대안 C8. 접지 판정은 물리 기반 결합 판정(압력·스트로크·자세) + 탐침이고 ML/DL은 비교 후보다.
- 고친 곳: S6(만드는 것, 제어기 검증 항목 표 신설, 위험 ②, 체크리스트), 3.5절 제어기 트랙, 5절 결정 상태.

개정 2(2026-10-20): [dynamics_model.md](dynamics_model.md) 개정 5(기존 기준값 변경 없음, 새 키만)를 반영해 "개정 5 기준" 자리를 실제 내용으로 채웠다.
- V4: 크롤러 위 정착 ≥ 11.6 s, t = 0 모터 출발(다리 0 m), 다리별 $e_{op}$ 계단 정지, 첫 접지 = 후방 쌍. 기준은 `reference.json / lift_V4_compliant_crawler`다. 개정 1의 "접지 − 10 mm 출발" 안은 지웠다.
- V7: 모드 투영 $\eta=\Phi^TMq$(`mode_shapes_rev5`)를 기본으로 하고 ERA/SSI는 대안으로 둔다.
- V14는 시험 다리를 RL+로 바꾼다(`V14_rev5`). V15는 (a) 단방향 상승, (b) 0 → 10 → 0 mm 왕복으로 나눈다(`V15_rev5`).
- 크롤러 규약은 YAML 새 키 이름(`contact.crawler.*`, `simulation.settle_on_*`)으로 참조한다. R8 크롤러 적용은 개정 5에서 확인됐다.
- V8(a) 배치, V9 매끄러운 시험, V11b 스텝별 판정, 정착 32 s, β 감도 감쇠 고정이 개정 5 문구와 같은지 확인했다(차이는 V9 ② 창 5 s, 최종 자세 비교 3주기 평균, β 감도에서 $g_n$·부싱 $k_t$도 고정 — 반영함).
- 실행 시간을 다시 계산했다(4절).

개정 1(2026-10-20): dynamics-expert 검토 [chrono_build_plan_review.md](chrono_build_plan_review.md)(판정 "수정 후 진행", 19건) 가운데 cad-expert 몫을 반영했다.
- 초기 조건: 해석 정적해로 시작한다. 안 되면 정착 ≥ 32 s. 정착 상태는 저장해 재사용한다(#2).
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
- V4·V14·V15 기준값과 크롤러 감쇠는 dynamics-expert가 [dynamics_model.md](dynamics_model.md) **개정 5**에서 다시 정한다(#1, #4, #5, #9). → 개정 2에서 실제 내용으로 채웠다.
- 3절을 실제 뼈대(`pyproject.toml`, 하위 패키지 5개, `tests/conftest.py`)에 맞췄다. 4절 실행 시간을 다시 계산했다.

공통 사항:
- 입력(읽기만 함): `CLAUDE.md`, `README.md`, `params/rexome33.yaml`, `docs/dynamics_model.md`(개정 5), `docs/actuator_L2_feasibility.md`, `analysis/dynamics/actuator_L2_feasibility.json`, `docs/chrono_stick_friction_test.md`, `scripts/chrono/test_stick_friction.py`, `docs/hydraulic_circuit.md`, `analysis/dynamics/reference.json`, `analysis/chrono/stick_friction.json`, `docs/chrono_build_plan_review.md`, `docs/imu_cabin_and_accuracy_review.md`(개정 3), `docs/control_candidates_comparison.md`(개정 3).
- 판정 기준은 `docs/dynamics_model.md` 5절 V0~V17이다. 이 문서는 기준을 새로 만들지 않고 단계에 배치한다.
- 담당(CLAUDE.md 작업 규칙):
  - **cad**(cad-expert): Chrono 모델·시뮬레이션 스크립트
  - **dyn**(dynamics-expert): V 판정
  - **py**(python-expert): 제어기·IMU 모델·데이터 처리
- 작업량: 소 = 에이전트 호출 1회, 중 = 2~3회, 대 = 4회 이상.

## 0. 요약

| 단계 | 목표 | 모델 | 통과 기준(V) | 담당 | 작업량 | 시뮬레이션 길이 / 예상 벽시계(직렬, 4병렬) |
|---|---|---|---|---|---|---|
| **S0** | 공통 기반: 로더·타입·규약 단위 시험, 부싱 회귀(히스테리시스 포함), 정착 상태 저장, 비용 측정 | — | V0(규약 부분), 블록 회귀 | cad (+py: 타입 검토) | 중 | 약 30 s / 1분 |
| **S1** | 상부체 + 고정 다리(운용 신장) + 지면 부싱(t = 0)으로 수평 정적, 정착 상태 저장 | L1 | V0, V1, V2, V3, V13 | cad → dyn | 중 | 45~120 s / 1~2분 |
| **S2a** | 지면 부싱 동특성 진단과 경사 정적 | L1(모터·크롤러 없음) | V7 진단(1·2차), V12, V13 | cad → dyn | 중 | 약 85 s / 1.5분 |
| **S2b** | 속도 모터, 크롤러 접촉(2×9 구), 접지 이벤트 부싱 생성·소멸, 크롤러 위 정착 상태 저장 | L1 | V0(모터 부호, 크롤러 배열·재질·충돌 필터), V11(공중 다리), V13, 이벤트 단위 시험 | cad → dyn | 중 | 약 92 s / 1.5분 |
| **S3** | 수치 감쇠 확인 → 들어 올림(모터 출발 → 계단 정지) → 다리 단독 신장, Δt 확정 | L1 | V8(a), V4, V5, V6, V9 | cad → dyn | 대 | 약 745 s / 12.5분, 약 4분 |
| **S4** | 6개 모드(모드 투영), 에너지 수지, β 감도 | L1 | V7(6모드), V8(b), β 감도 | cad → dyn | 중 | 약 510 s / 8.5분, 약 3분 |
| **S5** | 오거 3단계 | L1 | V10, V0(오거 합성) | cad → dyn | 소 | 약 165 s / 3분 |
| **S6** | 센서 진값, 210 bar 힘 포화(물리 스텝마다), 제어기 경계 | L1 | V11b, V17 기록 경로 | cad + py → dyn | 중 | 약 100 s / 2분 |
| **S7** | L2b-NSC | L2b-NSC | V0~V13(L2b-NSC 열, V4 첫 접지 15.04 s), V14(RL+) | cad → dyn | 대 | 약 1,970 s / 10~20분, 3~5분 |
| **S8** | 실 마찰, 카운터 밸런스, D2 외란 | L2b-NSC(+L1 V17) | V15(a)(b), V17, V8(b) | cad → dyn | 대 | 약 2,055 s / 11.5~21.5분, 4~6분 |
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
| R7 | 부싱 감쇠는 입력의 2배로 작용한다. 입력 = $c_t/2$ | 블록 시험 2.3 | V0. V7에서 ζ ≈ 0.10이면 위반 |
| R8 | 모든 SMC 재질(패드 구, 크롤러 구, 바닥 패치)은 $k_t=g_t=\mu=0$이다. 접선은 지면 부싱(L1) 또는 NSC(L2b)가 맡는다. `ChLoadBodyBodyBushingPlastic`은 쓰지 않는다. 크롤러 μ(YAML `contact.crawler.friction` 0.5)는 L1에서 쓰지 않고, L2b-NSC 크롤러 접촉에만 쓴다 | `dynamics_model.md` 4.1·4.2. 크롤러 적용은 **개정 5에서 확인됨**(4.2절 크롤러 행, 10절 `contact.crawler.smc_material`) | V0. 크롤러 접지 구간의 수평 표류는 판정하지 않고 기록만 한다 |
| R9 | `GetPos()` 등은 참조를 돌려준다. `probes.py`에서만 읽고 즉시 복사한다 | 블록 시험 4절 | 단위 시험 |
| R10 | 쿼터니언은 wxyz다(scipy xyzw와 섞지 않는다). 자세는 ZYX 내재 오일러각으로 쓴다 | `dynamics_model.md` 1.1 | `frames` 단위 시험 |
| R11 | 적분기는 `EULER_IMPLICIT_LINEARIZED`다. 솔버는 L1 `SPARSE_QR`(Pardiso MKL 비교), L2b-NSC `PSOR` 50회. `SetContactStiff` 같은 실행 설정은 V8(a)와 본 실행에서 같게 둔다 | `dynamics_model.md` 4.2·4.3, 검토 #3 | V8(a), V9, V13 |
| R12 | 기준값은 런타임에 `reference.json`(과 개정 5 이후 문서가 지정하는 파일)에서 읽는다. **키는 전체 문자열 상수로만 쓰고**(괄호·공백 포함) 키 존재 시험으로 막는다 | CLAUDE.md, 검토 #16 | `verify/reference.py` 시험 |
| R13 | 크롤러 접촉(개정 5): 트랙 2개 × 구 9개로 둔다. 배열은 `contact.crawler.sphere_layout.spheres_per_track`, `.track_centre_y_m`, `.x_range_m`, `.sphere_radius_m`(구 바닥 = `ground.crawler_bottom_z_m`)이다. 재질은 `contact.crawler.kn_per_sphere_N_m`, `contact.crawler.gn_per_sphere_1_s`(구당 감쇠 / 상부체 바디 질량. 크롤러 구가 상부체 바디에 붙어 있으므로 $m_{eff}$ = 상부체 질량), $k_t=g_t=\mu=0$(`contact.crawler.smc_material`)이다. 감쇠 근거 키는 `contact.crawler.damping_ratio_heave`, `contact.crawler.damping_total_N_s_m`이다. 크롤러 밑에 **패드 패치와 별도인 바닥 패치**를 두고 크롤러 구와 같은 재질 값을 준다. 값은 이 문서에 복사하지 않는다(YAML 키는 cad-expert가 `export_params.py`에 추가 중) | 검토 #9, `dynamics_model.md` 개정 5 4.2·10절 | V0(개정 5 추가 항목), S2b 크롤러 정착 |
| R14 | 충돌 패밀리: 바닥, 상부체(크롤러 구 포함), 로드 구를 서로 다른 패밀리로 둔다. 로드–상부체 쌍과 로드–크롤러 쌍을 끈다(`contact.crawler.collision_filter`). 크롤러 구는 상부체 패밀리라 한 번에 꺼진다. API는 `GetCollisionModel().SetFamily` / `SetFamilyMaskNoCollisionWithFamily`(pychrono 10에서 S1에 확인) | 검토 #18, 개정 5 V0 추가 | V0, V13 "다리당 접촉점 1" |
| R15 | 지면 부싱 복귀 사상은 $N\leftarrow\max(N,0)$으로 한다. 부상은 "$N\le0$이 $n_{lift}$스텝 연속"일 때, 재접지는 "$N>N_{th}$"일 때 판정한다(히스테리시스). 부싱 생성·소멸 횟수와 시각을 기록한다. $n_{lift}$와 $N_{th}$는 가정(7절) | 검토 #10 | S2b 이벤트 시험, V6, V8(b) |
| R16 | 정착 상태 저장·재사용: `snapshot()`이 바디 위치·자세·속도, 모터 위치, $s_{ref}$, 부싱 고정점·상태, 시스템 시각, 사용한 파라미터 sha256을 담는다. `restore()`는 같은 sha256일 때만 허용한다 | 검토 #2 | S0 왕복 시험(저장 → 복원 → 1 s 진행이 이어 돌린 결과와 같음) |

## 2. 단계별 계획

기준값 키 표기: 파일 이름 뒤에 JSON 경로를 ` / `로 이어 **전체 문자열**로 적는다. `<level>`은 `top`, `middle`, `bottom` 중 하나다. 예: `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / contact_force_N`.

초기 조건 규칙(검토 #2, 모든 정적 판정에 적용):
1. **해석 정적해로 시작**한다. 상부체 위치·자세는 V2 침투·V3 자세 기준값(`reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / static_penetration_or_compression_mm`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / static_attitude_deg (roll, pitch)`)에서 구한다. L2b-NSC는 같은 하위 키를 `L2b_NSC_force_motor_axial_spring_lateral_bushing` 아래에서 읽는다. 부싱은 t = 0에 접선력 0으로 만든다. 그 뒤 10 s 정착 + 판정 창.
2. 패드 위 상태를 해석 정적해로 시작할 수 없으면 정착을 **≥ 32 s**(`simulation.settle_on_pads_min_s`)로 둔다. 근거: 1차 로킹 ζ 0.0129, 1.785 Hz에서 $\tau=1/(\zeta\omega)$ = 6.9 s이고, 1/100 감쇠에 $\tau\ln100$ ≈ 32 s가 든다. 크롤러 위 정착(다리 0 m)은 **≥ 11.6 s**(`simulation.settle_on_crawler_min_s`, 크롤러 위 최대 τ 2.52 s × ln 100)다. 크롤러 정착 자세로 초기화한 뒤 이 시간을 둔다(`dynamics_model.md` 개정 5 4.5절 1).
3. 정착 결과는 R16 스냅숏으로 `results/states/`에 저장한다. 뒤 단계 시나리오는 이 상태에서 시작한다.

### S0 공통 기반

- **목표**: 같은 규약·파라미터·기록 형식을 쓰게 한다. 블록 시험 구현을 라이브러리로 옮겨 결과가 같은지 확인한다. 정착 상태 저장을 만든다. 전체 규모 스텝 비용을 잰다.
- **만드는 것**(3.1절의 "계획" 모듈):
  - `params`, `frames`, `types`, `engine`, `record`
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
| 파라미터 로더 | YAML 원문과 같은 값, 문자열로 읽힌 수치 0건 | 같은 float | `params/rexome33.yaml` |
| 부싱 회귀 2° 10 s | 미끄럼 0, 탄성 변위 | 미끄럼 < 1×10⁻³ mm, 탄성 ±0.1 % | `stick_friction.json / cases / name = "Bushing 2deg"` |
| 부싱 회귀 수평 v0 | 진동수, ζ | ±0.1 %, ±2 % | `stick_friction.json / cases / name = "Bushing flat v0"` |
| 부싱 회귀 30° 2 s | 미끄럼 거리 | ±0.5 % | `stick_friction.json / cases / name = "Bushing 30deg (tan>mu, must slide)"` |
| 히스테리시스(R15) | 단일 블록을 들었다 놓기: 생성 1, 소멸 1, chatter 0 | 횟수 일치 | 이 계획 |
| 스냅숏 왕복(R16) | 저장 → 복원 → 1 s 진행 결과가 이어 돌린 결과와 같음 | 위치 차 ≤ 1×10⁻¹² m | 이 계획 |
| V0(규약 부분) | R1·R2·R6 | 일치 | 1절 |

- **의존**: 없음.
- **위험**: PyYAML 부동소수 표기 함정이 있다. 로더가 수치를 `float`로 강제하고 실패하면 예외를 낸다. 블록 시험 스크립트는 회귀 기준으로 그대로 둔다.
- **담당·작업량**: cad 중. 타입(`types`)은 py가 검토한다.
- **체크리스트**
  - [x] 패키지 뼈대, `pyproject.toml`(pytest·ruff 설정, 마커 `chrono`·`sim`·`slow`), `tests/conftest.py` (2026-10-20, 사용자 승인으로 생성됨)
  - [ ] `params` + 전 키 왕복 시험
  - [ ] `make_system()`(R1·R2·R11)
  - [ ] `GroundBushingCoulomb`(R15 포함), 블록 회귀 3건과 히스테리시스 시험
  - [ ] 스냅숏 저장·복원(R16)
  - [ ] `verify/reference` 전체 문자열 키 상수와 존재 시험(R12)
  - [ ] 전체 규모 스텝 비용 재측정(4절)

### S1 상부체 + 고정 다리 + 지면 부싱, 정적

- **목표**: 다리를 운용 신장 $e_{op}$에 고정하고 지면 부싱을 t = 0에 둔 상태로 수평 바닥 정적값을 맞춘다. 3단계 정착 상태를 저장한다.
- **만드는 것**:
  - `chrono/bodies`: 상부체 `auger_levels.<level>`(관성 텐서 전체), 다리 이동부 4개, 바닥(다리별 패치 + 크롤러 패치)
  - `chrono/contact`: 로드 바디에 구 1개(r = 0.06 m), 재질(R5·R8), 충돌 패밀리(R14)
  - 다리 고정: `ChLinkLockLock` 또는 속도 0 모터
  - `chrono/probes`, `scenarios/settle`(해석 정적해 초기화), `verify/checks`의 V0~V3·V13
- **입력 키**:
  - `superstructure.auger_levels.<level>.*`
  - `legs.<leg>`: `moving_part.*`, `pad_bottom_center_retracted_m`, `attachment_point_m`, `pad.swivel_center_above_pad_bottom_m`
  - `contact.rigid_floor.L1.*`, `contact.rigid_floor.L1.derivation.operating_extension_m`
  - `contact.rigid_floor.geometry`
- **산출물**: `results/S1/`, `results/states/S1_L1_<level>.npz`, `analysis/chrono/verify_S1_L1.json`
- **통과 기준**(V1은 3단계 모두)

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V0 | 질량·무게중심·관성 = YAML. $g_n$, R8 재질, 바닥 1e9 kg, 부싱 입력 $c_t/2$, 패드 구와 패치 재질 값 같음 | 상대차 ≤ 1×10⁻⁹ | YAML |
| V1 | 접촉력, 실린더 힘, 합 | 합 ≤ 1×10⁻⁴, 다리별 ≤ 1 % W/4 | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / contact_force_N`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / cylinder_force_N`, `reference.json / statics / total_weight_incl_rods_N` |
| V2 | 침투 | ±5 % | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / static_penetration_or_compression_mm` |
| V3 | roll, pitch | ±0.002° | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / static_attitude_deg (roll, pitch)` |
| V13 | 정착 10 s 뒤 정지 5 s: 자세 드리프트 < 1×10⁻⁴°, 접촉력 변동 < 0.1 % W/4, NaN 없음, 다리당 접촉점 1 | — | `dynamics_model.md` 4.5 |

- **의존**: S0.
- **위험**:
  - ① SMC 재질 합성식이 미확인이다(전·후 $k_n$이 다름). 다리별 패치로 나누고 V2로 실제 $k_n$을 역산한다.
  - ② `GetContactForce()` 프레임이 미확인이다. 로드를 기울인 단위 시험과 `ReportContactCallback` 합으로 교차 확인한다.
  - ③ 해석 정적해 초기화가 V2·V3 기준값을 그대로 쓰므로 판정이 순환할 수 있다. 판정은 10 s 정착 뒤 값으로 한다. 초기값과 같게 머무는지가 곧 평형 확인이다. 초기화 없이 ≥ 32 s 정착한 사례 1건(top)으로 같은 값에 가는지 교차 확인한다.
- **담당·작업량**: cad 중, dyn 판정 소.
- **체크리스트**
  - [ ] V0 질량 특성 자동 비교(3단계)
  - [ ] 다리별·크롤러 바닥 패치, 재질, 충돌 패밀리(R14) API 확인
  - [ ] 해석 정적해 초기화 + 부싱 t = 0
  - [ ] 패드별 수직력: 프레임 확인, 콜백 교차
  - [ ] 초기화 없는 32 s 정착 교차 1건
  - [ ] 정착 상태 저장(3단계)

### S2a 지면 부싱 동특성 · 경사 정적

- **목표**: 모터·크롤러 없이 지면 부싱이 접선 강성·감쇠·정지 마찰을 제대로 내는지 가린다. V7 진단이 실패하면 원인이 부싱 쪽으로 좁혀진다.
- **만드는 것**:
  - `scenarios/impulse`: 이름은 뼈대 그대로 쓰고, 내용은 **초기 속도 가진**이다
  - `scenarios/slope`: 바닥 바디 회전, 레벨링 자세에서 구가 경사면에 닿은 위치에 놓고 t = 0에 부싱 생성, 중력 램프
  - `verify/metrics`: 다채널 식별(S4와 공용)
- **입력 키**: S1 전부. V12 신장은 `reference.json / slope_V12 / <case> / extension_m`을 쓴다. `<case>`는 `ground roll 0 deg, pitch 2 deg`, `ground roll 2 deg, pitch 0 deg`, `ground roll -2 deg, pitch 1.5 deg`다.
- **산출물**: `analysis/chrono/verify_S2a_L1.json`
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V7 진단 | 저장된 S1 top 상태에서 roll·pitch 방향 초기 속도. 1·2차 진동수, 창 ≥ 20 s | ±3 %. 약 3.06 / 4.16 Hz면 부싱 누락, ζ ≈ 0.10이면 $c_t$ 입력 오류, ζ ≈ 0.001이면 $g_n$·바닥 질량 오류 | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top / f_damped_Hz`(앞 2개) |
| V12 | 중력 0 → $g$ 램프(2~5 s, 기본 3 s) 뒤 정착, **마지막 3 s 평균**의 접촉 수직력·수평력. 미끄럼 = 부싱 고정점 누적 이동 | 수직 ±1 % W/4, 수평 ±10 % 또는 ±0.2 kN, 미끄럼 < 0.1 mm, 탄성 변위 ±10 % | `reference.json / slope_V12 / <case> / L1` |
| V13 | 위와 같음 | — | — |

- **의존**: S1.
- **위험**:
  - 중력 램프 중에도 모드가 들뜬다. 램프 길이를 1차 주기(0.56 s)의 4배 이상으로 두고, 램프 뒤 10 s 정착 + 3 s 평균으로 한다.
  - 신장 반올림(0.1 mm)이 하중에 미치는 영향은 ≤ 0.26 kN이다(검토 #8). 수평력 허용(±0.2 kN)과 같은 크기이므로 결과 보고에 함께 적는다.
- **담당·작업량**: cad 중, dyn 판정 소.
- **체크리스트**
  - [ ] 초기 속도 가진(roll, pitch)
  - [ ] 경사 바닥 + t = 0 부싱 + 중력 램프
  - [ ] V12 3경우, 마지막 3 s 평균, 항복 스텝 수 기록

### S2b 모터 · 크롤러 · 접지 이벤트

- **목표**: 다리를 모터로 움직이고, 크롤러 접촉을 넣고, 접지할 때 부싱을 만들고 부상할 때 없애는 이벤트 로직(R15)을 확인한다.
- **만드는 것**:
  - `chrono/actuators.L1SpeedActuator`: `ChLinkMotorLinearSpeed`, `SetAvoidPositionDrift(true)`, 가이드 PRISMATIC, $|u|\le v_{max}$, 스트로크 끝 차단, **모터 계단 정지**
  - 크롤러 구 배열(R13)
  - 접지 이벤트 부싱
  - `scenarios/stroke`(상부체 고정, 다리 공중)
- **입력 키**:
  - `actuator`: `stroke_m`, `max_speed_m_s`, `extension_direction`
  - `legs.<leg>.extension_range_m`
  - `contact.crawler.*`(R13의 키 전부: `sphere_layout.*`, `kn_per_sphere_N_m`, `gn_per_sphere_1_s`, `damping_ratio_heave`, `damping_total_N_s_m`, `smc_material`, `collision_filter`), `simulation.settle_on_crawler_min_s`
  - `ground.crawler_bottom_z_m`
- **산출물**: `analysis/chrono/verify_S2b_L1.json`, `results/states/S2b_crawler_<level>.npz`(크롤러 위 정착 상태)
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V0 | 모터 +속도 1 s → 패드 −z로 $v$·1 s, 모터 반력 부호 | 부호 일치 | — |
| V0(크롤러, 개정 5 추가) | 구 개수·위치·반지름, 구당 $k_n$·$g_n$, $k_t=g_t=\mu=0$, 크롤러 패치 재질 값 같음, 로드–상부체·로드–크롤러 쌍 꺼짐 | 상대차 ≤ 1×10⁻⁹, 설정 일치 | YAML `contact.crawler.*` |
| V11 | **상부체 고정, 다리 공중**에서 큰 속도 명령과 끝을 넘는 명령 | 속도 ≤ $v_{max}(1+10^{-3})$, 위치 −1×10⁻⁴ ~ 0.6801 m, 0 → 0.68 m 시간 ±0.05 s | YAML `actuator.stroke_m`, `actuator.max_speed_m_s`, `actuator.full_stroke_time_s` |
| 이벤트 | 한 다리를 내려 접지 → 들어 올려 부상 → 재접지 | 생성·소멸 횟수가 사건 수와 같음, chatter 0 | R15 |
| 크롤러 정착 | 다리 0 m, 크롤러 정착 자세로 초기화 후 ≥ 11.6 s(`simulation.settle_on_crawler_min_s`) | 정착 자세 $u_z$·pitch를 기준해와 비교(참고, 판정은 S3 V4). 크롤러 위 모드(pitch / roll / heave) 진동수 기록 | `reference.json / lift_V4_compliant_crawler / layouts`, `reference.json / lift_V4_compliant_crawler / crawler_on_floor_modes (default layout, legs at 0)` |
| V13 | 모터 구속 위반 ≤ 1×10⁻⁶ m, 접촉점 수 | — | — |

- **의존**: S1(S2a와 병행 가능).
- **위험**:
  - ① 크롤러 YAML 키는 cad-expert가 `export_params.py`에 추가하는 중이다. 키가 YAML에 생기기 전에는 크롤러 정착을 돌리지 않는다(값을 코드에 적지 않는다).
  - ② L1 모터 반력과 실린더 힘의 관계(로드 관성 포함)를 정적에서 "접촉력 − 로드 무게"와 비교한다.
- **담당·작업량**: cad 중, dyn 판정 소.
- **체크리스트**
  - [ ] 모터 축·부호(R4)
  - [ ] V11(공중 다리)
  - [ ] 크롤러 구 배열·패치·재질(R13), 패밀리(R14)
  - [ ] 접지·부상 이벤트(R15)
  - [ ] 크롤러 위 정착 상태 저장(3단계)

### S3 수치 감쇠 → 들어 올림 · 정착 → 다리 단독 신장, Δt 확정

- **목표**: Δt를 정하기 전에 수치 감쇠를 확인한다. 실제 운용 순서를 재현한다. 하중 민감도와 $F_{min}$·부상 문턱을 맞춘다.
- **만드는 것**:
  - `scenarios/lift`(개정 5 절차): $t<0$ 다리 0 m로 크롤러 위에서 정착한다(S2b 저장 상태 = 크롤러 정착 자세 초기화 + ≥ 11.6 s). $t=0$에 네 모터가 동시에 $+v_{max}$로 출발한다(시각 원점 = 모터 출발). 다리마다 자기 $e_{op}$에서 **계단 정지**한다(후방 17.246 s, 전방 17.696 s). 마지막 정지 뒤 10 s 정착한다. 정지 시각과 그때 다리 속도를 기록한다. 개정 1의 "접지 − 10 mm 출발" 안은 쓰지 않는다(시각 원점이 기준해와 달라짐).
  - `scenarios/leg_step`: FL 0.5 mm/s로 +1 / +5 mm, 0.1 mm/s 연속 신장, FL− 방향
  - `verify/metrics`: 정착값, 문턱 교차 보간, 수렴비, 접지 시각 기구학 예측 $t_i=\mathrm{gap}_i/v_{max}$(Chrono가 잰 크롤러 정착 자세에서 패드 바닥–바닥 간격)
  - `scripts/chrono/run_verify.py --jobs N`
- **입력 키**: S2b 전부, `control.F_min_cylinder_N`, `simulation.crawler_clearance_m`, `simulation.settle_on_pads_min_s`, `contact.rigid_floor.L1.derivation.operating_extension_m`(계단 정지 신장)
- **산출물**: `analysis/chrono/verify_S3_L1.json`, Δt 확정 요청(dyn 판정 뒤 YAML 재생성)

L1 기준값 경로 머리: `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top /`(아래 표의 키는 이 뒤에 붙는 전체 문자열이다).
- **통과 기준**(실행 순서대로)

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V8(a) | 감쇠 0($g_n$ = 0, 부싱 $c$ = 0), 모터 잠금, 항복 없는 작은 진폭의 초기 속도 자유 진동, **창 ≥ 60 s**, Δt와 2Δt. 접촉·솔버 설정은 본 실행과 같다(R11) | 에너지 증가 ≤ 1 % $E_{kin,0}$. 로킹 수치 감쇠비(모드 투영 1차) ≤ 0.1 × 설정 ζ. **ζ_num(2Δt)/ζ_num(Δt) = 2 ± 20 %**. 에너지가 늘면(음의 수치 감쇠) 실패 | `reference.json / time_step / L1_numerical_damping_bound_s (omega1 dt/2 <= 0.1 zeta1, top)`, L1 머리 + `zeta`(1차) |
| V4 | 위 lift 절차 | **첫 접지 다리가 후방 쌍이고 시각 15.006 s ±0.05 s**(RR, RL은 1 ms 차). 전방 접지·크롤러 이탈·최종 크롤러 여유는 기록만(참고). 마지막 정지 뒤 V1·V3 기준. 잔류 진동 포락선 ζ ±30 %, 마지막 정지 10 s 뒤 roll·pitch 진폭 < 0.001°. 기준해는 YAML 구 배열(2×9)을 쓸 때만 유효하다. **배열을 바꾸면** Chrono가 잰 정착 자세의 기구학 예측 $t_i=\mathrm{gap}_i/v_{max}$와 ±0.05 s로 비교한다 | `reference.json / lift_V4_compliant_crawler`(하위 `procedure`, `time_origin`, `layouts`, `residual_after_last_stop_linear_L1 (deg, max \|dev\| over one 1st-rocking period)`) |
| V5 | 저장된 S1 상태에서 FL +1 mm, +5 mm(0.5 mm/s) 뒤 정착 | ΔF 최대 성분 ±5 %, 자세 ±5 % | L1 머리 + `dF_per_mm_FL_N`, L1 머리 + `droll_dpitch_per_mm_FL_deg` |
| V6 | FL을 0.1 mm/s로 계속 신장(FL+, FL−) | 다리 일치, 문턱 ±5 % | L1 머리 + `F_min_threshold_single_leg (cylinder force = F_min)`, L1 머리 + `liftoff_threshold_single_leg (contact force 0)` |
| V9 | Δt, Δt/2, Δt/4. **차수(오차비)는 매끄러운 시험에서만** 잰다: ① V5 FL +1 mm 계단 응답의 과도 최대 하중(RL), ② 정착 상태에서 초기 속도 자유 진동(V7 1차)의 $t$ = 5 s 모드 진폭·위상. **V4는 차만** 판정한다. 정적 값은 Δt와 무관하므로 비를 내지 않는다 | 정적 하중 ≤ 0.1 % W/4, 최종 자세 ≤ 1×10⁻⁴°(마지막 1차 로킹 3주기 평균끼리), 과도 최대 하중 ≤ 1 %. ①·②의 오차비 2 ± 20 %. V4 접지 시각 차는 Δt 양자화(≤ 2×10⁻⁴ s)까지 허용 | `dynamics_model.md` 개정 5 V9 |
| 감도(1건) | 정지를 감속 램프로 바꾼 V4 | 기록만 | — |

- **의존**: S2a, S2b.
- **위험**:
  - ① V8(a)가 실패하면 V9와 Δt 확정을 하지 않는다. 그때는 dyn과 HHT 적분기 또는 Δt 축소를 협의한다.
  - ② V6 0.1 mm/s는 사례당 약 150 s다. 0.5 mm/s 결과와 한 번 비교해 준정적임을 확인한 뒤 병렬로 돌린다.
  - ③ 부상(V6 FL−)에서 R15가 도는지 생성·소멸 기록으로 확인한다.
- **담당·작업량**: cad 대, dyn 판정 중(V9로 Δt 확정).
- **체크리스트**
  - [ ] V8(a) Δt·2Δt, 60 s
  - [ ] lift(크롤러 정착 상태, t = 0 모터 출발, 다리별 $e_{op}$ 계단 정지, 정지 기록), 첫 접지 = 후방 쌍 15.006 s 판정
  - [ ] V5, V6(FL+, FL−)
  - [ ] V9(매끄러운 시험으로 차수, V4는 차만)
  - [ ] 병렬 실행기와 meta(params·reference sha256, dt, 솔버, pychrono 버전, 벽시계)

### S4 6개 모드 식별 · 에너지 수지 · β 감도

- **목표**: 6개 모드의 진동수·감쇠와 감쇠·항복을 켠 에너지 수지를 맞추고, β 감도를 Chrono로 재현한다.
- **만드는 것**:
  - `verify/metrics`의 **모드 투영**(개정 5 기본): 상부체 운동을 `mode_shapes_rev5`의 기준점에 대한 6자유도 변위 $q$로 바꾸고 $\eta=\Phi^TMq$로 모드 좌표를 만든 뒤, 모드마다 감쇠 정현을 맞춰 진동수·ζ를 얻는다. 6채널 ERA/SSI는 교차 확인용 대안이다. `mode_content`는 에너지 비율이라 투영에 쓰지 않는다.
  - 초기 속도 가진 6종(roll, pitch, heave, surge, sway, yaw, 부싱 항복이 없는 크기): 창은 1·2차 ≥ 20 s, 3~6차 1~2 s(τ ≈ 0.3~0.4 s)
  - 에너지 항: 운동 + 중력 + SMC $\tfrac12k_n\delta^2$ + 부싱 $\tfrac12k_t|d|^2$, $D_{visc}$(부싱 실제값 = 입력의 2배), $D_{slip}$, 모터 일
  - `params` 실행 시 오버라이드(YAML은 고치지 않음)
- **입력 키**: S3 전부. β 감도는 다음 키를 쓴다.
  - 강성: `reference.json / L1_beta_sensitivity_top / beta_6.9e+08 / k_L1_N_m`, `reference.json / L1_beta_sensitivity_top / beta_1.0e+09 / k_L1_N_m`, `reference.json / L1_beta_sensitivity_top / beta_1.6e+09 / k_L1_N_m`
  - 판정 값: `penetration_mm`, `static_pitch_deg`, `dF_per_mm_FL_N`, `FL+_F_min_mm`, `FL+_liftoff_mm`, `f_Hz_top`
- **산출물**: `analysis/chrono/verify_S4_L1.json`, β 감도 표
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V7 | 6개 모드 진동수·ζ(모드 투영) | 진동수 ±3 %, ζ ±30 % | L1 머리 + `f_undamped_Hz`, `f_damped_Hz`, `zeta`. 모드 형상: L1 머리 + `mode_shapes_rev5` 아래 `Phi (rows = coordinates, cols = modes in f_undamped_Hz order, first 6)`, `mass_matrix (same coordinates)`, `reference_point_m (rotations about it, translations of it; body axes, level body = world)`, `coordinates`, `projection` |
| V8(b) | V12 + 큰 수평 초기 속도(항복 발생)에서 에너지 수지 | 잔차 ≤ 1 %, $D_{slip}/\sum\mu N|\Delta a|$ 1.00~1.05. 부싱 생성·소멸 횟수 기록 | — |
| β 감도 | 개정 5 규칙: 바꾸는 것은 L1 패드 $k_n$(`k_L1_N_m`) 하나뿐이다. **$c_n$, $c_t$, $g_n$, 부싱 $k_t$는 기본값 그대로.** 판정은 정적값(침투, 정착 pitch, FL +1 mm ΔF, FL+ $F_{min}$·부상 문턱)과 **비감쇠 진동수**(`f_Hz_top`)만 한다. ζ는 판정하지 않는다. V6는 비용이 크면 1.6 GPa 한 값만 돌린다(0.69 GPa는 약 200 s) | V2·V3·V5·V6·V7 진동수와 같은 허용 | 위 β 키 |

- **의존**: S3(Δt 확정).
- **위험**: 5.8~8.0 Hz 네 모드가 가깝다. 모드 투영으로 분리하고, 투영 잔차(다른 모드 섞임)가 크면 ERA/SSI로 교차 확인한다. $\Phi$는 기준해 강성(Chrono 입력과 같은 $k_n$, $k_t$)에서 나온 값이므로, β 감도처럼 강성을 바꾼 실행에는 쓰지 않고 ERA/SSI를 쓴다.
- **담당·작업량**: cad 중, dyn 판정 중.
- **체크리스트**
  - [ ] 초기 속도 6종 + 모드 투영($\Phi$, $M$, 기준점) + ERA/SSI 교차
  - [ ] V8(b) 에너지 수지
  - [ ] β 3값(감쇠 고정), V6는 비용에 따라 1.6 GPa만
  - [ ] (선택) 로드측 챔버 +10 % $k_v$ 1건

### S5 오거 3단계

- **목표**: 상단·중단·하단에서 정적 하중과 로킹 진동수를 확인한다.
- **만드는 것**: 레벨을 시나리오 매개변수로 노출한다. 오거 합성 검사(`fixed_part` + `auger_moving_set_at_cad_pose`를 z로 Δ 이동 → `auger_levels.<level>`)를 단위 시험으로 둔다.
- **입력 키**: `superstructure`: `auger_levels.*`, `auger_moving_set_at_cad_pose.*`, `fixed_part.*`, `auger_level_order`
- **통과 기준**

| V | 판정 | 허용 | 기준값 키 |
|---|---|---|---|
| V0(오거) | 합성 질량·무게중심·관성 = `auger_levels.<level>` | ≤ 1×10⁻⁹ | YAML |
| V10 | 저장된 S1 상태(3단계)에서 V1, roll·pitch 초기 속도(창 ≥ 20 s)로 1·2차 | 하중 ≤ 0.1 % W/4, 진동수 ±3 %, 상단 < 중단 < 하단 | `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / contact_force_N`, `reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / <level> / f_damped_Hz`(앞 2개) |

- **의존**: S4(식별 도구).
- **담당·작업량**: cad 소, dyn 판정 소.
- **체크리스트**
  - [ ] 오거 합성 단위 시험
  - [ ] 3단계 V1·V7(1·2차)

### S6 압력 센서 · 힘 포화 · 제어기 경계

- **목표**: 제어기가 보는 관측과 주는 명령을 엔진 독립 형식으로 고정한다. 210 bar 힘 포화를 구현하고 350 bar 지표를 기록 경로에 넣는다.
- **만드는 것**
  - cad:
    - `sensors/truth`: IMU 장착점 비력·각속도 진값(장착점 기본값 = 캐빈 바닥 아래 상부 프레임, 기체 좌표 (0.20, 0.88, 0.30) m, **가정**: x·y는 운전실 bbox 중심, z는 프레임 최저 모서리 0.275 m + 바닥판·브래킷 0.025 m. 불확실 범위 x −0.60…0.90, y 0.50…1.25, z 0.24…0.45 m. 인자로 바꿀 수 있게 둔다), 헤드 압력 $p=F_{cyl}/A_p$, 스트로크(모터 위치, 보정값 = 모터 위치 − $F_{cyl}/k_{oil}(e)$)
    - 힘 포화: 구동기 모델 안에서 **물리 스텝마다** 판정한다. $F_{cyl}\ge$ `actuator.max_force_extend_N`이고 $u>0$이면 $u=0$. $F_{cyl}\le$ −`actuator.max_force_retract_N`이고 $u<0$이면 $u=0$. 제어 주기(20 ms)로만 판정하면 9.4 kN이 넘친다.
    - 단일 다리 시험 모델: 패드를 바닥에 **$k_n$과 같은 강성의 양방향 스프링**(`ChLinkTSDA` 또는 부싱 축 방향, 감쇠 = $c_n$ 실제값)으로 묶는다. 강체로 묶으면 강체 모터와 직렬이라 힘이 부정이 된다. 접촉으로는 수축 시험의 인장을 낼 수 없다.
    - `runner`: 제어 주기 영차 유지(기본 20 ms = 100스텝)
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
| 2 | ±0.2° 정확도 | IMU 장착점 (0.20, 0.88, 0.30) m, 2차 필터, 데드밴드 0.03°, 센서 등급 이상 / 우수 영점 후 / 보통 영점 후 / 보통 영점 후 + 반복성 / 보통 출하. 오거 3단계 × 경사 4가지 | 정상상태 실제 자세(준비 완료 뒤 마지막 5 s 최대 절대값) + 장착 몫 0.03° ≤ 0.2°. 축소 모델 기대(C2, 장착 몫 더함): 우수 0.089°, 보통 0.117°, 보통 + 반복성 0.178°는 통과, 보통 출하 0.222°는 불가. Chrono 시뮬레이션은 장착 몫을 모델에 넣지 않으므로 판정 때 더한다 |
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
  - ② IMU 장착점은 캐빈 바닥 아래 상부 프레임으로 정했지만 좌표 (0.20, 0.88, 0.30) m는 CAD bbox에서 잡은 **가정**이다(바닥판·브래킷 높이는 CAD에 없음). 로킹 순간 회전 중심이 IMU 아래 2.0~5.8 m(지면 아래)라 높게 달수록 겉보기 기울기 증폭이 커진다. 장착점은 인자로 받고, 실기 좌표가 오면 바꾼다. 캐빈 몸체(방진 마운트 위)에는 달지 않는다.
  - ③ L1 스트로크와 실제 스트로크가 약 5.1 mm 다르다. 두 신호를 모두 낸다.
- **담당·작업량**: cad 중, py 중, dyn 판정 소.
- **체크리스트**
  - [ ] `Measurements`·`Command` 타입 확정(py 검토)
  - [ ] 압력·스트로크 가상 센서
  - [ ] 스텝별 힘 포화 + 양방향 스프링 단일 다리 V11b
  - [ ] 350 bar 지표 기록
  - [ ] py: IMU 오차 모델, Controller 프로토콜, 빈 제어기로 60 s 폐루프 연기 시험
  - [ ] IMU 진값 장착점 기본값 (0.20, 0.88, 0.30) m(가정)과 인자 변경 단위 시험
  - [ ] py: 센서 등급 5종(이상·우수 영점 후·보통 영점 후·보통 + 반복성·보통 출하), 2차 필터(τ 0.5 s × 2)
  - [ ] py: C2 제어기(대안 C8)와 물리 기반 결합 접지 판정 + 탐침
  - [ ] 제어기 검증 항목 1~8(L1), 9는 S7·S8

### S7 L2b-NSC

- **목표**: 운용안 B 재판정 모델을 만든다. L1과 같은 시나리오(초기 조건 규칙, 초기 속도 가진, 중력 램프 포함)로 L2b-NSC 열을 통과시키고 V14를 판정한다.
- **만드는 것**:
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
| V4(NSC) | L1과 같은 lift 절차. 크롤러가 NSC 강체라 가라앉지 않는다 | **첫 접지 = 후방 쌍 15.04 s** ±0.05 s, 나머지는 L1 V4와 같음 | `reference.json / operating_point / time_to_touch_s`(후방 값) |
| V13(NSC) | PSOR 50회에서 정지 5 s 접촉력 변동 | ≤ 0.1 % W/4 | `dynamics_model.md` 5절 |
| V14 | 최대 레벨링 경사 3경우(pitch +3.86°, roll 5.91°, 대각 3.31°)에서 V12 절차 + **RL 단독 신장(RL+)** 민감도·$F_{min}$ 문턱·부상 문턱 + 로킹. FL+는 pitch+에서 FL이 스트로크 끝이라 할 수 없다. RL+는 세 경우 모두 스트로크 여유가 있다 | 민감도·문턱 ±5 %, $F_{min}$ 도달 다리 일치, 진동수 ±3 %, 미끄럼 < 0.1 mm | `actuator_L2_feasibility.json / A_extension_dependence / V14_rev5`(하위 `method`, `V14_test_leg`, `cases`) |

- **의존**: S6, S4의 식별·에너지 도구.
- **위험**:
  - ① 가이드 해제: 헤더에 `SetGuideConstraint(cx, cy, crx, cry, crz)`가 있다(`ChLinkMotorLinear.h:42`). Python 노출은 미확인이다. 안 되면 FREE 가이드 + `ChLinkLockAlign`으로 한다.
  - ② 힘 법칙을 양해로 갱신한다(안정 한계 1.1×10⁻³ s ≫ 2×10⁻⁴ s). 문제가 보이면 `ChLinkTSDA`(자유 길이 = $s_{ref}$)로 바꾼다.
  - ③ PSOR 반복 오차가 V1·V13을 못 맞추면 반복 수를 올리고 비용을 다시 잰다.
  - ④ 크롤러 접지 구간은 NSC 강체 다점 접촉이라 하중이 부정이다. 이 구간 하중은 판정하지 않는다.
  - ⑤ NSC 패드별 수직력 읽기는 V1로 교차 확인한다.
- **담당·작업량**: cad 대, dyn 판정 중.
- **체크리스트**
  - [ ] 가이드 x·y 해제 API 확인
  - [ ] 힘 법칙, $s_{ref}$, 스텝별 포화
  - [ ] 횡 부싱
  - [ ] V0~V13(배열 앞 6개)
  - [ ] V4(NSC, 첫 접지 15.04 s)
  - [ ] V14 3경우, RL+(`V14_rev5`)
  - [ ] L1 대 L2b-NSC 비교표

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
  - ② ζ(Q6)가 D2 계단 응답의 공진 크기를 정한다. ζ 감도를 함께 돌린다.
  - ③ V15(a)는 부상에서 끝나므로 R15 이벤트(부상 판정 $n_{lift}$스텝)가 문턱 판정 시각을 늦출 수 있다. 부상 문턱은 접촉력 0 교차 시각(보간)으로 재고 이벤트 시각과 따로 기록한다.
  - ④ 기준해는 로드 무질량·잠김 강성 2.17×10⁸ N/m 가정이다. 0.1 mm/s에서도 로드 관성 효과가 남는지 0.05 mm/s 1건으로 확인한다.
- **담당·작업량**: cad 대, dyn 판정 중.
- **체크리스트**
  - [ ] 실 마찰 요소 + V15(a) 단방향 상승(부상까지), V15(b) 0 → 10 → 0 mm 왕복
  - [ ] 카운터 밸런스 옵션(`lock_valve`)
  - [ ] D2 하중(결정 뒤)
  - [ ] V17 L1·L2b-NSC

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
| V0 | pad_body + rod_body = moving_part | ≤ 1×10⁻⁹ | YAML, `params/rexome33_checks.json` |
| V16 | 파라미터 확정 전: 합력 상대차 ≤ 1×10⁻³, 에너지 증가 없음. 확정 후: Bekker 평판 식 | 확정 뒤 dyn이 정함 | `dynamics_model.md` 5절 |

- **의존**: S7(+S8 선택). **SCM 파라미터 결정이 선행 조건**이다.
- **위험**: SCM 격자 비용과 시간 간격이 미측정이다. 침하가 남은 스트로크(0.279 / 0.289 m)를 넘을 수 있다.
- **담당·작업량**: cad 대, dyn 판정 중.
- **체크리스트**
  - [ ] SCM 파라미터 확보
  - [ ] 패드/로드 분리 + 구면 조인트 + 경사 제한
  - [ ] 단일 패드 비용·격자 수렴
  - [ ] V16

## 3. 코드 구조

### 3.1 현재 상태와 계획 모듈

패키지는 설치하지 않는다. pytest는 `pyproject.toml`의 `pythonpath = ["src"]`로, 스크립트는 경로 추가로 `src/`를 불러온다.

| 경로 | 상태(2026-10-20) | 내용 |
|---|---|---|
| `pyproject.toml` | **있음** | 도구 설정만 둔다. pytest(`minversion 8.0`, `pythonpath = ["src"]`, `testpaths = ["tests"]`, `--strict-markers`, 마커 `chrono`·`sim`·`slow`)와 ruff(줄 100, py312, isort first-party `outrigger_sim`) |
| `src/outrigger_sim/__init__.py` | **있음**(docstring만) | 엔진 독립 핵심 + Chrono 백엔드 |
| `src/outrigger_sim/chrono/__init__.py` | **있음**(docstring만) | 계획 모듈: `system`, `bodies`, `contact`, `ground_bushing`, `lateral_bushing`, `actuators`, `loads`, `scm`, `probes`, `model` |
| `src/outrigger_sim/control/__init__.py` | **있음**(docstring만) | Controller 프로토콜과 제어기(py) |
| `src/outrigger_sim/scenarios/__init__.py` | **있음**(docstring만) | 계획 모듈: `settle`, `lift`, `leg_step`, `impulse`(초기 속도 가진), `slope`, `stroke`, `single_leg`, `disturbance_d2` |
| `src/outrigger_sim/sensors/__init__.py` | **있음**(docstring만) | 계획 모듈: `truth`(cad), `imu_model`(py) |
| `src/outrigger_sim/verify/__init__.py` | **있음**(docstring만) | 계획 모듈: `reference`, `metrics`, `checks` |
| `src/outrigger_sim/{params, frames, types, engine, runner, record}.py` | 계획(S0) | 로더, 좌표, 타입, SimEngine 프로토콜, 실행기, 기록·스냅숏 |
| `tests/conftest.py` | **있음** | 세션 픽스처 `project_root`, `params_path` |
| `tests/unit/`, `tests/chrono/`, `tests/verify/` | **있음**(`.gitkeep`만) | 3.4절 |
| `scripts/chrono/run_verify.py` | 계획(S3) | 단계별 V 실행기 |
| `scripts/chrono/test_stick_friction.py` | 있음 | S0 회귀 기준으로 그대로 둔다 |

계획 모듈의 역할:
- `params`: YAML을 고정 dataclass로 읽는다. 수치는 float으로 강제한다. level과 모델을 고르고, 실행 시 오버라이드(β 등)를 받는다.
- `frames`: wxyz 쿼터니언, ZYX roll·pitch
- `types`: Command, Measurements, TruthState, Record 필드
- `engine`: SimEngine(reset, step, apply_command, measure, truth, snapshot, restore, close)
- `runner`: 영차 유지, 기록 간격
- `record`: npz + meta.json, 스냅숏(R16)
- `chrono/model`: 스텝 뒤 훅 순서를 정한다(지면 부싱 R15 → 구동기 포화·$s_{ref}$ → 기록)
- `verify/reference`: 전체 문자열 키 상수(R12)
- `verify/metrics`: 정착값, 문턱 교차, ERA/SSI 다출력 식별, 에너지 수지, 수렴비, 접지 시각 기구학 예측
- `verify/checks`: `CheckResult(id, item, value, ref, tol, unit, passed, ref_key)`

### 3.2 엔진 독립 인터페이스 (MuJoCo 병행 대비, Q8 미정)

- 엔진 의존 코드는 `chrono/`에만 둔다. `scenarios`, `runner`, `record`, `verify`, `sensors/imu_model`, `control`은 `SimEngine`과 `Record`만 본다.
- `Record`는 고정 이름 배열이다: `t`, `body_pos`, `body_quat_wxyz`, `body_vel`, `body_omega`, `F_cyl[4]`, `F_contact_n[4]`, `F_contact_t[4,2]`, `s_motor[4]`, `s_ref[4]`, `u_cmd[4]`, `u_applied[4]`, `bushing_anchor[4,3]`, `bushing_events`, `energy.*`.
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
| 단위 | `tests/unit/` | 없음 | 각 < 1 s | 로더, 좌표, 복귀 사상·히스테리시스 수식, 기준값 키 존재, 오거 합성 |
| 엔진 규약 | `tests/chrono/` | `chrono` | 수 초 ~ 1분 | V0 규약, 부싱 블록 회귀, 스냅숏 왕복 |
| V 시험 | `tests/verify/test_S<n>_*.py` | `sim`, 긴 것은 `slow` | 수 분 ~ 수십 분 | `verify/checks`를 호출해 assert |

- 판정 실행은 `scripts/chrono/run_verify.py --stage S<n> --model L1 --level top --jobs N`이 한다. 결과는 `results/verify/<stage>/<run_id>/`(npz, report.json, 그림), 정착 상태는 `results/states/`, 요약은 `analysis/chrono/verify_<stage>_<model>.json`(git 추적)에 둔다.
- pytest와 `run_verify.py`는 같은 `checks`를 쓴다. 자동 통과/실패는 사전 점검이고 최종 판정은 dyn이 한다.
- 일상 회귀는 `pytest -m "not slow"`로 돌린다. `results/`는 `.gitignore`에 있다.

### 3.5 제어기 트랙 (py, 참고)

| 시점 | 내용 | 모델 |
|---|---|---|
| S3 뒤 | 개루프 명령 재생으로 runner·Record 확인 | L1 |
| S6 뒤 | IMU 오차 모델(센서 등급 우수/보통, 영점 후·출하; 장착점 캐빈 바닥 아래 상부 프레임 (0.20, 0.88, 0.30) m 가정) + 2차 필터(τ 0.5 s × 2) + **C2 제어기**(대안 C8) + 물리 기반 결합 접지 판정·탐침으로 폐루프. **±0.2°**(데드밴드 0.03°, 장착 몫 0.03° 더해 판정), $F_{min}$, 3단계. S6 제어기 검증 항목 1~8 | L1 |
| S7·S8 뒤 | 큰 경사·실 마찰·D2 재판정. 압력만 vs 결합 접지 판정 비교(S6 검증 항목 9). Chrono 접촉력을 라벨로 한 ML/DL 판정기 학습 데이터 생성($F_s$·β·경사·오거·노이즈 무작위화)과 물리 기반 판정기 비교 | L2b-NSC |
| S9 뒤 | 연약 지면 재판정 | L2b-NSC + SCM |

## 4. 실행 비용 추정

측정 근거(2026-10-19, 이 PC 28코어, pychrono 10.0.0, Δt 2×10⁻⁴ s):

| 구성 | µs/스텝 | 출처 |
|---|---|---|
| 단일 블록 SMC / SMC + 부싱 훅 / NSC PSOR 50 | 9 / 33 / 9 | `analysis/chrono/stick_friction.json` |
| 전체 규모 L1(바디 5, 모터 4, 패드 구 4, 부싱 4, SPARSE_QR) | 146 / **163**(4다리 훅) | scratchpad 비용 측정(물리 미검증, 2 s) |
| 전체 규모 NSC(바디 5, 힘 모터 4, PSOR 50) | 35 / **43**(힘 법칙 훅) | 같은 측정 |

계획 단가(가정)는 다음과 같다.
- L1: **0.2 ms/스텝 = 시뮬레이션 1 s당 벽시계 1 s**
- L2b-NSC: **0.06 ms/스텝 = 1 s당 0.3 s**(크롤러·부싱이 붙으면 2배까지 볼 수 있음)
- Δt/2, Δt/4 실행은 스텝 수만큼 늘린다. 2Δt는 절반이다. 크롤러 구 배열과 SCM은 포함하지 않았고, S0에서 다시 잰다.

| 단계 | 주요 사례(시뮬레이션 길이) | 합계(Δt 환산) | 예상 벽시계 직렬 / 4병렬 | 장시간 |
|---|---|---|---|---|
| S0 | 블록 회귀·히스테리시스·스냅숏·비용 측정 | 약 30 s | 1분 | 아니오 |
| S1 | 3단계 × (정적해 초기화 + 정착 10 s + 정지 5 s) = 45 s, 초기화 없는 교차 1건 37 s. 초기화가 안 되면 3 × 37 s | 45~120 s | 1~2분 | 아니오 |
| S2a | V7 진단 roll·pitch 2 × 20 s, V12 3 × (램프 3 s + 정착 9 s + 평균 3 s) | 약 85 s | 1.5분 | 아니오 |
| S2b | V0 2 s, V11 35 s(공중 다리, 접촉 없음), 이벤트 시험 20 s, 크롤러 위 정착 3단계 × 11.6 s ≈ 35 s | 약 92 s | 1.5분 | 아니오 |
| S3 | V8(a) 60 s(Δt) + 60 s(2Δt) = 90 s. V4(저장된 크롤러 정착 상태에서 모터 출발 → 마지막 정지 17.7 s + 정착 10 s) 27.7 s × (기준 + 감속 램프 감도) = 55 s. V5 +1 / +5 mm 32 s. V6 FL+·FL− 2 × 150 s = 300 s. V9 매끄러운 시험(① V5 +1 mm 12 s + ② 자유 진동 5 s) × (2 + 4) = 102 s, V4 × (2 + 4) = 166 s | 약 745 s | 12.5분 / 약 4분(V6 150 s 사례가 병목) | 직렬은 예, 병렬 아니오 |
| S4 | V7 초기 속도 6종(2 × 20 s + 4 × 2 s) 48 s. V8(b) 30 s. β 3값 × (정적 15 s + V5 32 s + 진동수 48 s) = 285 s. V6 1.6 GPa만(문턱 약 8 mm, 약 100 s). 로드측 감도(선택) 50 s | 약 510 s | 8.5분 / 약 3분 | 아니오 |
| S5 | 3단계 × (V1 15 s + roll·pitch 2 × 20 s) | 약 165 s | 3분 | 아니오 |
| S6 | V11b 단일 다리 20 s, 센서 20 s, V17 경로 15 s, 폐루프 연기 60 s | 약 115 s | 2분 | 아니오 |
| S7(NSC) | S1~S5의 top 시험 재실행(β 제외) 약 1,180 s, V14 3경우 × (V12 15 s + RL+ 민감도 32 s + RL+ 연속 신장 부상까지 최대 약 175 s + 로킹 40 s) ≈ 790 s | 약 1,970 s | 10분(단가 2배면 20분) / 3~5분 | 직렬은 예 |
| S8 | NSC: V15(a) 4 × 부상까지(약 13~14 mm, 0.1 mm/s) ≈ 545 s, V15(b) 4 × 200 s = 800 s, 관성 확인(0.05 mm/s, 12 kN) 260 s, D2 3단계 × 2 로크 밸브 × 30 s = 180 s, ζ 감도 2 × 3 × 30 s = 180 s → 약 1,965 s. L1 V17 3 × 30 s = 90 s(1 s/s) | 약 2,055 s | 11.5~21.5분 / 4~6분 | 직렬은 예 |
| S9 | SCM 미측정(1~10 ms/스텝 가정 시 정착 32 s 1건에 3~27분) | — | 미정 | 예 |

장시간 규칙:
- 한 번의 실행이 10분을 넘을 것 같으면 에이전트가 직접 띄우지 않는다. `run_verify.py`의 명령 전체·예상 시간·출력 경로를 **메인 세션 권고**로 넘긴다.
- S3·S4·S7·S8은 `--jobs 4`이면 10분 안에 들어오므로 병렬로 돌린다. S9는 비용을 잰 뒤 정한다.

## 5. 미정 사항과 결정 시점

| 항목 | 필요한 단계 | 결정 시점 | 미정이면 |
|---|---|---|---|
| 기체 좌표 원점 | S0 | S0 시작 전 | CAD 원점(오프셋은 `frames` 한 곳) |
| 크롤러 YAML 키 반영(`contact.crawler.*`, `simulation.settle_on_*`; cad-expert가 `export_params.py`에 추가 중. 값은 개정 5에서 결정됨) | S2b, S3 | **S2b 크롤러 정착 전** | 크롤러 정착·V4 보류 |
| 지면 경사 시험 범위 | S2a, S7 | S2a 전 | V12 3경우 |
| Δt 확정 | S4 이후 | S3 V8(a)·V9 뒤(dyn) | 2×10⁻⁴ s |
| MuJoCo 역할(Q8) | 병행 시 S1~S4 재사용 | **S4 끝 전** | 인터페이스만 |
| 자세 정확도 목표 | S6 뒤 폐루프 | **결정됨**(2026-10-20): ±0.2°, 데드밴드 0.03°, IMU 현장 영점 교정 의무 | — |
| IMU 장착 위치(Q4) | S6 | **결정됨**(2026-10-20): 캐빈 바닥 아래 상부 프레임. 좌표 (0.20, 0.88, 0.30) m는 가정, 실기 좌표가 오면 갱신 | — |
| 자세 신호 필터 | S6 뒤 폐루프 | **결정됨**(2026-10-20): 2차 저역통과(1차 τ 0.5 s × 2단) | — |
| 센서 모델 선정(노이즈·바이어스·지연 사양), 제어 주기 | S6 | **S6 전** | 가정치(영점 오차 허용 ≤ 2.27 mg = 0.13°, ±0.2° 캐빈·데드밴드 0.03° 예산; 등급 4종으로 감도. 20 ms) |
| 제어기 구조(D1) | S6 뒤 폐루프 | **잠정 결정**(2026-10-20): C2, 대안 C8. 접지 판정은 물리 기반 결합 판정 + 탐침, ML/DL은 비교 후보 | — |
| 제어기 세부(탐침 빈도, 비틀림 목표, 게인), roll·pitch 목표 범위 | S6 뒤 폐루프 | **S6 끝 전** | `control_candidates_comparison.md` 7.1절 값 |
| D2 외력 크기·작용 시간·작용점(Q9) | S8 | **S7 시작 전**(늦어도 S8 전) | 정착 상태 지표만 |
| 카운터 밸런스 교체(Q10), 실 마찰 크기 | S8 | 막지 않음 | 두 옵션 구현, 감도 0/2/5/12 kN |
| 감쇠 ζ(Q6) | S8 | S8 전 | 0.05 + 감도 |
| SCM 파라미터 | S9 | **S9 전** | S9 보류 |
| 마스트 굽힘(Q4) | S6, S8 | 자료가 오면 | 강체 |
| 실제 운용 중량 | 전부 | 언제든 | 경우 C. 바뀌면 YAML 재생성 → dyn `run_reference.py` → 저장 상태 폐기(sha256 불일치) → V 회귀 |

## 6. 위험 목록과 대응

| # | 위험 | 단계 | 대응 |
|---|---|---|---|
| 1 | SMC 재질 합성식 미확인(패드 전·후, 크롤러) | S1, S2b | 다리별·크롤러 바닥 패치 + 같은 재질(R13), V2로 실제 $k_n$ 역산 |
| 2 | `GetContactForce()` 프레임 미확인, NSC 반력 환산 | S1, S7 | 단위 시험, `ReportContactCallback` 교차, V1 |
| 3 | 모터 Z축·반력 부호 | S2b | V0(R4) |
| 4 | 감쇠 규약 위반 | 전부 | V0 자동 검사, V7 진단 규칙 |
| 5 | 중력 기본 0, 충돌 시스템 누락 | 전부 | `make_system()` 한 곳 |
| 6 | `GetPos()` 참조 저장 | 전부 | `probes`만 읽고 즉시 복사 |
| 7 | 정착 과도가 길어(τ 6.9 s) 정적·정지 판정이 흐려짐 | S1~S5 | 해석 정적해 초기화, 안 되면 ≥ 32 s, 정착 상태 저장·재사용(R16) |
| 8 | 크롤러 접촉이 접지 시각을 바꿈(정착 자세 $u_z$ −3.82 mm, pitch +0.0687°) | S3 | 개정 5 절차(크롤러 위 정착 ≥ 11.6 s, 첫 접지 = 후방 쌍 15.006 s). 기준해는 2×9 배열에서만 유효(배열 감도 14.927~15.032 s) → 배열을 바꾸면 기구학 예측과 비교 |
| 9 | 부상·재접지 chatter, $N<0$ | S2b, S3, S8 | R15($\max(N,0)$, 히스테리시스, 횟수 기록) |
| 10 | 크롤러 접촉점 수 변동, YAML 키 미반영 | S2b, S3 | 구 배열 2×9(R13), 키가 YAML에 생기기 전에는 크롤러 시나리오 보류 |
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
| 24 | Python 훅 비용 | S3 이후 | 4다리 벡터화, Pardiso 비교, 사례 병렬 |
| 25 | 부싱 감쇠 2배·SMC 질량당 감쇠의 버전 의존 | 전부 | S0 회귀가 버전 변경을 잡음 |
| 26 | SCM 비용·격자·침하 | S9 | 단일 패드 측정 먼저 |

## 7. 이 계획의 가정

| 가정 | 값 | 비고 |
|---|---|---|
| 스텝 단가 | L1 0.2 ms, L2b-NSC 0.06 ms(2배까지) | 전체 규모 측정 + 센서·기록 몫. S0에서 다시 잼 |
| 제어 주기 | 20 ms | `dynamics_model.md` 6.2 상한 |
| 정착 길이(해석 정적해 없음) | 패드 위 ≥ 32 s, 크롤러 위 ≥ 11.6 s | $\tau\ln100$. τ = 6.9 s(1차 로킹, ζ 0.0129) / 2.52 s(크롤러 위 최대). `dynamics_model.md` 개정 5 4.5절 1 |
| 중력 램프 | 3 s(2~5 s 범위) | 1차 주기 0.56 s의 4배 이상 |
| 부상·재접지 판정 | $n_{lift}$ = 5스텝(1 ms), $N_{th}$ = 100 N | R15. S2b 이벤트 시험으로 조정 |
| 크롤러 형상 | 트랙 2개 × 구 9개(개정 5, YAML `contact.crawler.sphere_layout.*`) | 접촉점 수 고정. 가정 값은 개정 5 문서 소관 |
| 바닥 패치 | 다리별 4개 + 크롤러 1개 | 합성식 미확인 대응 |
| V4 시작점 | 크롤러 위 정착 상태, 다리 0 m, t = 0 모터 출발 | 개정 5 절차(기준해 시각 원점과 같음) |
| V15 관성 확인 | 0.05 mm/s 1건 | 기준해의 로드 무질량 가정 확인 |
| 사례 병렬 | 프로세스 4개 | 28코어에서 늘릴 수 있음 |
