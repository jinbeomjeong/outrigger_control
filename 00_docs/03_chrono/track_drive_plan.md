# 주행 시험 트랙(T): 실제 궤도 모델로 전진·후진 (계획, 2026-10-20)

작성: cad-expert. **계획 문서다.** 모델 코드·YAML·다른 문서는 고치지 않았다. 아래 "확인 결과"의 수치는 scratchpad 조사 스크립트(프로젝트 밖, 4절 끝 목록)로 이 PC에서 실행한 값이다.

- 사용자 결정(2026-10-20): 시험용으로 크롤러 하부체의 **스프로킷(유압 주행 모터 구동)** 을 돌려 궤도가 움직이고, 파일드라이버가 **전진·후진**하는 모션을 만든다. 방식은 **실제 궤도 모델**(Chrono Vehicle 궤도차량 계열: 슈 개별 바디 + 핀 연결, 스프로킷 이빨–슈 맞물림, 아이들러, 하부 롤러, 트랙 장력)이다. 접선력 근사나 위치 지정 이동은 쓰지 않는다.
- **스프로킷(주행 모터)은 앞쪽**(기체 +x, CAD +Z 끝 바퀴)이고 뒤쪽 끝 바퀴(Ø548)는 아이들러(장력 장치)다 — **사용자 확정(2026-10-20)**. CAD 형상 근거는 2.2절.
- 범위: 레벨링(마스트 수직 상태 자세 제어) 트랙과 **별개인 선택 트랙**이다. 레벨링 모델(L1/L2b)과 빌더·시나리오·기록을 분리한다(7절).
- 입력(읽기만 함): `CLAUDE.md`, `00_docs/00_roadmap.md`, `00_docs/03_chrono/chrono_build_plan.md`(R1~R16, 4절 비용), `00_docs/00_cad/cad_review.md` 8.6·9절, `01_cad/06_brep/derived/crawler/*`, `01_cad/06_brep/prototypes/0_1_1_746.bbrep`(B-rep 캐시, 단면 조사만), `03_src/outrigger_sim/chrono/system.py`, `06_analysis/01_chrono/01_cost/solver_benchmark.json`, `00_docs/01_dynamics/dynamics_model.md` 3.8절, `02_params/rexome33.yaml`(읽기만), `00_docs/00_cad/cad_origin_mass_imu.md` 2절(크롤러 질량).
- 담당: **cad**(cad-expert) 모델·시뮬레이션, **dyn**(dynamics-expert) 판정, **py**(python-expert) 엔진 독립 기록·그림 도구(필요 시).

## 0. 요약

| 항목 | 결론 |
|---|---|
| pychrono 10 궤도차량 가용성 | **사용 가능.** `pychrono.vehicle`에 `ChTrackedVehicle`, `TrackedVehicle`(JSON), `ChTrackAssemblySinglePin/DoublePin/BandBushing/BandANCF`, `ChTrackShoeSinglePin` 등, `ChSprocketSinglePin`, `ChTranslationalIdler`, `ChTranslationalDamperSuspension`/`ChRotationalDamperSuspension`, `ChTrackDrivelineBDS`/`ChSimpleTrackDriveline`, `ChTrackBrakeSimple`, `ChTrackedVehicleVisualSystemIrrlicht`, `RigidTerrain`, `SCMTerrain`이 import된다. JSON 템플릿(M113·Marder)을 **우리 `ChSystem` 안에** 만들어 2 s 주행까지 돌렸다(1.1절) |
| 사용자 정의 템플릿 | **JSON만 된다.** 추상 템플릿(`ChTrackShoeSinglePin` 등)은 Python에서 인스턴스를 만들 수 없다(`No constructor defined - class is abstract`, SWIG director 없음). JSON 사본을 고쳐(피치 0.1732 m, 이빨 11, 슈 57개) 읽는 것은 확인했다 |
| 권장 구성 | **단일 핀(SinglePin) 강체 슈 + 이상 회전 조인트**, 측마다 슈 44개(CAD), 스프로킷 앞·아이들러 뒤(사용자 확정), 하부 롤러 6개/측(강성 = 크롤러 D안 총 강성 1×10⁸ N/m 분배), 상부 롤러 1개/측(CAD, 트랙 길이 가운데 x 0.000 m, 답면 Ø120; `upper_run_check.json`), 섀시 = 상부체(경우 C) + 다리 이동부(수축 고정) − 궤도 부품, **NSC 접촉** |
| 구동 | 측별 유압 주행 모터. M1 이상 속도 모터(`ChLinkMotorRotationSpeed`, 스핀들 FREE) → M2 토크–속도 특성(릴리프 토크 한계·유량 속도 한계, `ChSprocket.ApplyAxleTorque`). 조향 없음(좌우 같은 명령) |
| 비용(추정) | 바디 약 121개(섀시 1 + 슈 88 + 스프로킷 2 + 아이들러 바퀴·캐리어 4 + 하부 롤러·암 24 + 상부 롤러 2; KKT 좌표 약 726). M113(바디 약 154 = 섀시 1 + 슈 127 + 스프로킷 2 + 아이들러 4 + 로드휠·암 20, 좌표 926) 실측 NSC PSOR 50 **6.0 ms/스텝**, BB 100 16.0 ms, SMC SPARSE_LU 2.0 ms → 우리 모델 NSC PSOR 약 4.5 ms/스텝(가정; 바디 수 비 0.79면 4.7 ms, 차 4 %는 추정 오차 안이라 단가는 그대로 둠). 10 s 주행: Δt 5×10⁻⁴ s 약 90 s, 1×10⁻⁴ s 약 7.5분 |
| 단계 | T0 CAD 추출 → T1 한쪽 트랙 공회전 → T2 양쪽 + 상부체 평지 정적 → T3 전진·후진·정지 + GIF → T4(선택) SCM. 작업 약 18~27시간, 계산 약 1~1.5시간(T4 제외) |
| 사용자 결정 필요 | 스프로킷 맞물림 모델(CAD 불일치, 2.2절), 주행 모터 사양·주행 속도, 트랙 장력, 주행 시 오거 위치, Δt·솔버 |

## 1. pychrono 10 가용성 확인 결과

### 1.1 실행한 조사 (2026-10-20, 이 PC, pychrono 10.0.0, Python 3.12.15)

| 조사 | 결과 |
|---|---|
| `import pychrono.vehicle` 이름 목록 | 666개. 궤도 관련: `ChTrackedVehicle`, `TrackedVehicle`, `ChTrackAssembly{SinglePin, DoublePin, BandBushing, BandANCF, Segmented, Band}`, `TrackAssembly{SinglePin, DoublePin, BandBushing, BandANCF}`, `ChTrackShoe{SinglePin, DoublePin, BandBushing, BandANCF, Segmented}`, `TrackShoeSinglePin`, `ChSprocket{SinglePin, DoublePin, Band}`, `SprocketSinglePin`, `ChIdler`, `ChTranslationalIdler`, `TranslationalIdler`, `ChTrackWheel`, `ChSingleTrackWheel`, `ChDoubleTrackWheel`, `ChTrackSuspension`, `ChTranslationalDamperSuspension`, `ChRotationalDamperSuspension`, `ChTrackDrivelineBDS`, `ChSimpleTrackDriveline`, `ChTrackBrakeSimple`, `ChTrackBrakeShafts`, `ChTrackContactManager`, `ChTrackCollisionManager`, `ChTrackCustomContact`, `ChTrackedVehicleVisualSystemIrrlicht`, `ChTrackedVehicleVisualSystemVSG`, `ReadTrackAssemblyJSON`, `ReadTrackWheelJSON`, `ReadIdlerJSON`, `ReadTrackSuspensionJSON`, `ReadTrackBrakeJSON`, `ReadDrivelineTVJSON`, `RigidTerrain`, `SCMTerrain`, `M113_*`. `ChDistanceIdler`는 **없다**(아이들러는 `TranslationalIdler`만) |
| 추상 템플릿 Python 상속 | 클래스 정의는 되지만 인스턴스 생성 실패(`No constructor defined - class is abstract`). `vehicle.py`에 director 코드 없음 → **C++ 가상 함수를 Python에서 덮어쓸 수 없다.** 사용자 정의는 JSON으로 한다 |
| 데이터 경로 | `veh.SetVehicleDataPath`/`GetVehicleDataFile` 있음. Chrono 데이터 `C:\ProgramData\miniforge3\envs\Chrono-dev\Library\data\vehicle\`에 M113·Marder 궤도 JSON 있음(Marder는 상부 롤러 `Rollers`, 슈 사이 부싱 `Bushing Data` 예) |
| 외부 시스템에 생성 | `veh.TrackedVehicle(system, json)` 서명 있음 → 프로젝트 `ChSystem`(중력 명시 R1, Bullet R2)에 넣을 수 있다. 확인함 |
| 구동 수단 | `ChSprocket.ApplyAxleTorque(T)`, `GetAxle()`(ChShaft), `GetGearBody()`, `GetAxleSpeed()`, `ChTrackedVehicle.DisconnectDriveline()` 있음. 스프로킷 기어 바디–섀시에 `ChLinkMotorRotationSpeed`(스핀들 FREE) 추가도 동작 |
| JSON 사본 수정 | M113 사본에서 피치 0.154 → 0.1732, 이빨 10 → 11, 슈 63 → 57로 바꿔 로드·1 s 실행 성공(`GetPitch()` 0.1732, `GetNumTeeth()` 11) |

기능 시험(헤드리스, 평지 `RigidTerrain` 200×20 m, μ 0.8, 0.5 s 정착 뒤 스프로킷당 −4,000 N·m 또는 속도 모터; 측정은 벽시계/스텝):

| 사례 | 시스템·솔버 | Δt [s] | 슈(좌/우) | 좌표 수 | 구속 수(접촉 포함) | 접촉 수 | **ms/스텝** | 비고 |
|---|---|---|---|---|---|---|---|---|
| M113 SinglePin(이상 핀 조인트) | NSC, BB 100회 | 5×10⁻⁴ | 63/64 | 926 | 5,159 | 1,466 | **16.0** | 2 s, 주행함 |
| 같음 | NSC, PSOR 50회 | 5×10⁻⁴ | 63/64 | 926 | 5,555 | 1,598 | **6.0** | 1 s |
| 같음 | SMC, SPARSE_LU + 잠금 | 5×10⁻⁴ / 1×10⁻⁴ | 63/64 | 926 | 761 | 253 / 189 | **2.0 / 2.0** | 1 s / 0.3 s |
| Marder SinglePin + 슈 사이 부싱, 상부 롤러 3 | SMC, SPARSE_LU + 잠금 | 5×10⁻⁴ | 77/78 | 1,154 | 182 | 362 | **5.1** | 1 s |
| M113 JSON 사본 수정 | NSC, BB 100회 | 5×10⁻⁴ | 57/64 | 890 | 5,156 | 1,475 | 13.6 | 1 s |
| M113 + 스프로킷 속도 모터 | NSC, BB 100회 | 5×10⁻⁴ | 63/64 | 928 | 5,080 | 1,439 | 15.9 | 1 s |

- 부호: `ApplyAxleTorque(−4000)`에서 `GetAxleSpeed()`가 +4.4 rad/s인데 차체는 −x로 갔다. 축 방향·좌우 부호 규약이 직관과 다르다 → **T1에서 단위 시험으로 부호를 정한다**(조사값은 판정에 쓰지 않음).
- M113 우측 JSON 슈 수가 좌측보다 1개 많다(데이터 파일 값). 우리 템플릿은 좌우 같게 만든다.
- 위 조사는 API 확인용이다. 물리 판정(정적 평형·미끄럼률)은 하지 않았다.

### 1.2 판정

- **Chrono Vehicle 궤도 템플릿을 JSON으로 쓰는 경로를 권장한다.** 슈–스프로킷 맞물림 접촉(`ChSprocketSinglePin` 기어 윤곽 사용자 정의 충돌), 아이들러 장력 장치, 트랙 조립 시 슈 자동 배치, 트랙 장력 출력(`GetTrackShoeTension`)을 그대로 쓴다.
- 대안(일반 `ChBody` + `ChLinkLockRevolute`로 직접 조립)은 쓰지 않는다. 슈 88개 배치·폐루프 조립, 스프로킷 이빨 접촉(일반 Bullet 메시 접촉이면 이빨–부싱 접촉이 불안정하고 비싸다), 장력 장치, 탈선 방지 가이드를 모두 새로 만들어야 한다. 추가 작업 약 15~25시간으로 추정한다. JSON 경로가 T1에서 막힐 때만(예: 23이빨 반피치 맞물림 실패, 2.2절) 스프로킷 부분만 대체 수단을 검토한다.
- Python 정의 템플릿이 안 되므로 **CAD → JSON 생성기**(T0)가 모델 정의의 단일 출처가 된다. 생성 JSON은 손으로 고치지 않는다(프로젝트 YAML 규칙과 같음).

## 2. 모델 구성안

### 2.1 좌표·단위

- Chrono Vehicle 규약(x 전방, y 좌측, z 상방, 스프로킷이 앞, 아이들러가 −x)이 **기체 좌표와 같다.** 차량 기준 프레임 = 기체 원점(CAD 원점 = 선회 링 볼트원 축 ∩ 데크 하면)으로 둔다. 지면 z = −1.0509 m(`ground.crawler_bottom_z_m`).
- SI(m, kg, s). CAD mm → m ×1e-3, mm³ → m³ ×1e-9, kg·mm² → kg·m² ×1e-6. 관성은 각 바디 무게중심 기준, 바디 축.

### 2.2 CAD에서 확인한 하부체 형상 (2026-10-20 조사, CAD 전역 mm, Y 상방)

크롤러 B-rep 캐시(`0_1_1_746.bbrep`, sha256 `d3142659…fbe6e`)와 `crawler_solids.csv`·`crawler_wheels.csv`에서 뽑았다. **이 하부체는 STEP 설명상 다른 기종(REXOME25)이다.**

| 항목 | 값 | 출처·방법 |
|---|---|---|
| **앞 끝 바퀴 링(스프로킷)** | **이빨 23개**, 각 간격 15.652° 균일(= 360/23), 이빨 끝 반지름 330.0 mm(Ø660), 이빨 뿌리 반지름 294.3 mm, 링 두께(X) 74 mm(X 1008~1082), 링 중앙 X = ±1045(트랙 중심면) | B-rep 단면(X = ±1045 평면) 반지름 윤곽, 좌·우 모두 23 |
| 앞 끝 바퀴 동축 부품 | Ø525 드럼(X 988~1153), Ø480 허브, Ø480.6 하우징형 솔리드(X 1150~1326, 트랙 중심 바깥쪽), 열린 셸 `SHELL 0:1:1:745`(Ø약 342, X 770~874, 좌측 앞 축 안쪽) | `crawler_solids.csv`, `parts.csv` 864행. 주행 모터·감속기 하우징으로 보임(**추정**) |
| **뒤 끝 바퀴(아이들러)** | 답면 Ø548, 플랜지 Ø573(폭 X 952~1140), 단면 윤곽이 **원형**(이빨 없음) | 같은 단면 방법 |
| 하부 롤러 | 측마다 6개, Ø194, 폭 242, 축 기체 x −0.884/−0.527/−0.170/+0.187/+0.544/+0.901 m, 축 z −0.7907 m | `crawler_wheels.csv` |
| 상부 롤러(캐리어) | **측마다 1개**(2026-10-21 정정) | 측마다 1개, 기체 x 0.000 m·z −0.3327 m(지면 위 718 mm)·y ±1.045 m, 답면 Ø120×35 mm 2개 + 가운데 플랜지 Ø140. 롤러·축·받침대가 한 솔리드라 이전 bbox 원형 조건에서 빠졌음(`upper_run_check.json`) |
| 끝 바퀴 축 | 앞 z_body +1.400 m, 뒤 −1.405 m(축 간 2.805 m), 축 높이 기체 z 약 −0.583 m | `crawler_wheels.csv` |
| **슈 수** | **측마다 44개**(핀·부싱·링크 쌍·슈 판 2종이 모두 44개씩 반복) | `crawler_solids.csv` 부피 반복군 |
| 피치 | 173.2 mm(핀 중심 간격 중앙값 173.2, 범위 172.8~177.6) | 핀 무게중심 고리 |
| 트랙 길이(핀 중심 체인) | 44 × 173.2 = **7,620.8 mm**. CAD 핀 다각형 둘레는 7,667.3 mm(한 곳 이상 간격이 넓음 — CAD 배치 오차로 보임, T0에서 확인) | 위 |
| 핀·부싱 | 부싱 외경 Ø58.8(길이 141.4), 핀 Ø36.3(길이 214), 동축 | 부피 반복군 bbox |
| 슈 판 | 폭(X) 600 mm인 솔리드 2종/피치(단면 bbox 75×130, 50×199 mm). 그라우저 끝 접지 폭은 422 mm(X 834~1256) | 크롤러 파생 캐시. 600과 422의 차이는 T0에서 형상으로 확인 |
| 피치당 부피·질량(추정) | 피치마다 반복되는 솔리드 합 7.33×10⁶ mm³ → 강재 7.85 g/cm³이면 **약 57.5 kg/피치**, 측당 약 2,530 kg | 반복군 합(44의 배수인 군만). 크롤러 전체는 STEP 상위 재질 강철 7.85로 11,271 kg(`cad_origin_mass_imu.md` 2절) |
| 스프로킷 위 핀 중심 반지름 | **336.0 mm**(감긴 핀 6개 모두) | 핀 무게중심 ↔ 앞 축 거리 |
| 아이들러 위 핀 중심 반지름 | 327.2 mm(감긴 핀 5개) | 같음 |

**스프로킷 위치 근거(사용자 확정과 일치)**: 이빨 링은 앞 축에만 있고(23이빨), 뒤 축 바퀴는 단면이 원형이다. 앞 축에는 하우징형 동축 솔리드와 열린 셸(주행 모터·감속기로 보임, 추정)이 있고 뒤 축에는 없다. Chrono Vehicle의 기본 배치(스프로킷 앞, 아이들러 뒤)와도 같다. → **해소(사용자 확정 2026-10-20).**

**CAD 맞물림 불일치(사용자 확인 필요)**: 23이빨 링은 피치 173.2 mm 체인과 정수로 맞물리지 않는다.
- 이빨 23개 = 홀수 이빨(반피치 맞물림, 부싱이 이빨 사이 홈을 하나 걸러 들어감)이면 한 바퀴에 11.5 피치다. 부싱 중심이 놓일 반지름은 $R = p/(2\sin(2\pi/23))$ = **321.0 mm**, 유효 구동 반지름 $r_{eff}=11.5\,p/2\pi$ = **317.0 mm**다.
- CAD에 그려진 핀 중심 반지름 336.0 mm는 한 바퀴 12.05 피치(= 12피치 스프로킷의 334.6 mm)에 가깝다. 부싱 반지름 29.4 mm를 빼면 부싱 안쪽 끝이 306.6 mm로, 이빨 끝(330 mm)과 뿌리(294.3 mm) 사이에 걸치지만 홈 간격(15.65°)과 피치 각(29.87°)이 맞지 않는다. 단순화 모델에서 링과 트랙을 따로 그린 것으로 보인다(추정).
- 선택지: **(a) 23이빨 반피치**(실제 형상 우선, $r_{eff}$ 317.0 mm) / (b) 12이빨 등가($r_{eff}$ 330.8 mm, CAD 핀 반지름 우선). 두 경우 같은 모터 속도에서 주행 속도가 4.3 % 다르다. 권장은 (a)이고, T1에서 Chrono `SprocketSinglePin`이 하나 걸러 맞물림을 처리하는지 확인한다. 안 되면 (b)로 바꾸고 차이를 보고한다.

### 2.3 트랙 조립(좌우 같음)

| 요소 | Chrono 템플릿(JSON) | 값의 출처 | 비고 |
|---|---|---|---|
| 트랙 조립 | `TrackAssemblySinglePin` | — | 좌 오프셋 +1.045 m, 우 −1.045 m(트랙 중심, CAD) |
| 슈 | `TrackShoeSinglePin`, 44개/측 | 피치 0.1732 m(CAD), 질량·관성(CAD 피치당 솔리드 합, T0), 높이(CAD), 접지 충돌 상자 = 그라우저 끝 패치(CAD 폭 0.422 m), 바퀴 접촉 상자 = 링크 레일 윗면(CAD) | 부싱 원통(`Cylinder Shape`): 반지름 0.0294 m(CAD 부싱), 앞·뒤 오프셋은 T1에서 정함(한 피치에 맞물림 점 1개가 되게) |
| 슈 연결 | **이상 회전 조인트**(템플릿 기본) | — | 부싱(`Bushing Data`)은 옵션. 실기 핀–부싱은 강체에 가깝고, 조인트가 둘레를 정확히 보존한다. NSC 수렴이 나쁘거나 부싱 강성 자료가 생기면 바꾼다 |
| 스프로킷 | `SprocketSinglePin` | 이빨 23(또는 12, 2.2절), 윤곽(이빨 끝·홈 원호 반지름·원호 중심 반지름·조립 반지름)은 T0 단면에서, 질량·관성은 링+드럼+허브(+모터 회전부 가정) | 앞 축 기체 (x 1.400, z −0.583) m |
| 아이들러 | `TranslationalIdler` + 장력 장치(스프링 예압·강성·감쇠) | 바퀴 Ø548·플랜지(CAD), 캐리어 이동 방향 기체 x | 뒤 축 기체 (x −1.405, z −0.583) m. 장력은 **가정**(5절) |
| 하부 롤러 | `RotationalDamperSuspension`(또는 `TranslationalDamperSuspension`) + `DoubleTrackWheel` 6개/측 | 바퀴 Ø194·폭 242(CAD), 축 위치(CAD). **강성: 크롤러 D안 총 강성 `contact.crawler.kn_total_N_m` 1×10⁸ N/m를 롤러 12개에 나눔(8.33×10⁶ N/m/롤러)**, 감쇠 `contact.crawler.damping_total_N_s_m`/12 | Chrono에는 강체 롤러 템플릿이 없어 짧은 암 + 비틀림 스프링으로 넣는다(등가 수직 강성 = 비틀림 강성/암²). 정적 하중에서 암이 설계 위치에 오도록 예압을 정한다. 이렇게 두면 L1 크롤러 구 배열(D안)과 같은 heave 강성이 되어 T2에서 교차 확인이 된다 |
| 상부 롤러 | 측마다 1개 | CAD(`upper_run_check.json`) | 궤도 JSON `"Rollers"`에 `DoubleTrackWheel`(Marder 예제)로 넣음, 반지름 0.060 m, Width·Gap 의미는 Chrono 소스로 확인. 회전부 질량·관성은 원통 절단 추정 17.16 kg·0.0368 kg·m²(축 기준, `crawler_upper_rollers.csv`, 가정) |
| 트랙 프레임 | 섀시에 강결합 | — | 트랙 프레임을 따로 두지 않는다(선회 링·센터 프레임·트랙 프레임은 상부체와 같은 강체) |
| 구동 | `DisconnectDriveline()` 후 측별 모터(3절) | — | 차동기·BDS는 쓰지 않는다(유압 모터가 측마다 직결) |
| 브레이크 | `TrackBrakeSimple`(최대 토크 가정) 또는 속도 0 유지 | 가정 | 주행 모터 주차 브레이크·카운터 밸런스 밸브를 근사 |

### 2.4 섀시(상부체)와 질량 정리

- 섀시 = `superstructure.auger_levels.<level>`(경우 C, 크롤러 전체 포함) + 다리 이동부 4개(`legs.<leg>.moving_part.*`, **수축 0 m 상태로 강결합**) **− 따로 모델링하는 궤도 부품**(슈 88개, 스프로킷 2, 아이들러 2(+캐리어), 하부 롤러 12(+암), 상부 롤러 2(`crawler_upper_rollers.csv`, 부품 22.5 kg/개)). 질량·무게중심·관성을 평행축 정리로 뺀다. 이렇게 해야 전체 질량·무게중심이 레벨링 모델과 같다.
- 아우트리거는 완전 수축이다. 패드 바닥 높이는 전방 −0.6998 m, 후방 −0.7120 m(면 색인)로 지면에서 약 0.34 m 떠 있다. 다리는 섀시와 한 바디로 둔다(모터·부싱 없음). 마스트는 수직, 오거 위치는 레벨링과 같은 3단계 중 선택(기본 상단, 9절 U5).
- 섀시 JSON(`RigidChassis`)의 `Components`에 섀시 값 하나를 넣는다(무게중심 위치 + 관성 텐서 전체, 곱관성 포함).
- 섀시 충돌: 끈다(지면·슈와 닿을 일이 없음). 패드 바닥 충돌은 넣지 않는다(주행 중 다리 수축).
- 섀시와 궤도 부품의 질량 합 = YAML 합(상대차 ≤ 1×10⁻⁹)을 T2 V0식으로 자동 비교한다.

### 2.5 지면·마찰

- **강체 지면: NSC 접촉을 기본으로 한다.** SMC는 Chrono 10에서 정지 마찰이 없다(`00_docs/03_chrono/chrono_stick_friction_test.md`: 2°에서 0.11 m/s 미끄럼). 주행 중 접지 슈는 지면에 대해 붙어 있어야(stick) 견인력이 생기고, SMC면 견인력이 미끄럼 속도로만 생겨 미끄럼률·정지 유지가 틀어진다. NSC는 Coulomb을 정확히 다루고, Chrono Vehicle 궤도차량 예제의 기본도 NSC다. L1의 지면 부싱 + Coulomb 처리는 슈 88개에 맞지 않는다(접지 슈가 계속 바뀜).
- SMC + SPARSE_LU(조사 2.0 ms/스텝, NSC PSOR의 1/3)는 **평지 공회전·형상 점검용 옵션**으로만 둔다(판정에 쓰지 않음).
- 지면: `RigidTerrain` 평면 패치(고정 바디). 슈–지면 마찰 μ = 0.5(`contact.crawler.friction`, 가정, 강–콘크리트 0.4~0.6). 슈–바퀴·스프로킷 μ는 가정(0.3, 금속–금속 윤활 없음 근사).
- 연약 지면은 T4에서 `SCMTerrain`(Bekker-Wong + Janosi 전단)로 한다. 파라미터는 레벨링 S9와 같은 문제로 미정이다.

### 2.6 솔버·적분기·Δt

- NSC: 적분기 `EULER_IMPLICIT_LINEARIZED`, 솔버 **PSOR 50회**(L2b 규약과 같음)로 시작하고, 정적 평형(T2)이 1 % 안에 들지 않거나 핀 구속 위반이 크면 BARZILAIBORWEIN 100회(조사 2.7배 비용)로 바꾼다. 섀시 대 슈 질량비가 약 670(38,556 / 57.5)으로 M113(약 430)보다 커서 반복 솔버 수렴이 더 나쁠 수 있다(위험 1).
- Δt: 개발 실행 **5×10⁻⁴ s**(Chrono 궤도차량 예제 관례). 판정 실행은 T1·T2에서 5×10⁻⁴ / 2.5×10⁻⁴ / 1×10⁻⁴ s 수렴을 보고 dyn이 정한다. 프로젝트 수치 감쇠 규칙(ωΔt/2 ≤ 0.1ζ)을 크롤러 위 heave(D안 8.730 Hz, ζ 0.05; `06_analysis/00_dynamics/reference.json`의 "crawler_on_floor_modes (layout D, legs at 0)")에 적용하면 Δt ≤ 0.2ζ/ω = 0.01/(2π × 8.730) ≈ 1.82×10⁻⁴ s(옛 2 × 9 배치 8.1 Hz에서는 1.96×10⁻⁴ s)이고, 규칙의 계단값은 그대로 1×10⁻⁴ s다. 주행 시험의 판정량(미끄럼률·속도·정적 하중)은 이 모드 감쇠에 덜 민감하므로 규칙 적용 여부를 dyn에 묻는다(5절).

## 3. 구동

### 3.1 유압 주행 모터 모델

| 모델 | 내용 | 쓰는 단계 |
|---|---|---|
| **M1 이상 속도** | 스프로킷 기어 바디–섀시 `ChLinkMotorRotationSpeed`(스핀들 FREE, 기존 회전 조인트와 중복 구속 없음), 속도 함수 = 사다리꼴(가속 램프·정속·감속 램프). 반력 토크 = 필요 토크로 기록 | T1, T2, T3 기본 |
| **M2 토크–속도 특성** | 매 물리 스텝 Python에서 $T = \mathrm{clip}(K_\omega(\omega_{cmd}-\omega),\ \pm T_{max})$, $|\omega|\le\omega_{max}$를 `ApplyAxleTorque`로 넣는다. $T_{max} = \Delta p_{relief} D_m i \eta_m / 2\pi$(릴리프 압력 한계), $\omega_{max} = Q\eta_v/(D_m i)$(유량 한계), $K_\omega$는 체적 효율(누설) 기울기에서 정한다 | T3 감도 |
| 정지 유지 | 명령 0 + 주차 브레이크(`TrackBrakeSimple`, 최대 토크 가정) | T3 |

- 감속비 $i$, 모터 배제량 $D_m$, 릴리프 $\Delta p$, 유량 $Q$는 **모른다**(5절). 사양이 오기 전에는 M1로 필요 토크를 구해 "필요 토크 ≤ 가정 $T_{max}$"만 보고한다.
- 조향은 범위 밖이다. 좌우에 같은 명령을 준다. 좌우 불균형(무게중심 y −1.5 mm)으로 생기는 요 표류는 기록만 한다.

### 3.2 시나리오 (가정, 사용자 확인)

| 이름 | 명령(스프로킷 기준 주행 속도 $v_{cmd}=\omega r_{eff}$) | 길이 |
|---|---|---|
| `drive_settle` | 명령 0, 브레이크, 정착 | 5 s(해석 초기화가 없으면 늘림) |
| `drive_forward` | 0 → +0.3 m/s 램프 2 s, 정속 6 s, 감속 2 s, 정지 유지 3 s | 13 s |
| `drive_backward` | 같은 형상, −0.3 m/s | 13 s |
| `drive_fwd_back` | 전진 → 정지 2 s → 후진(GIF용) | 약 26 s |

- 주행 속도 0.3 m/s(1.08 km/h)와 가속 0.15 m/s²는 **가정**이다(파일드라이버 저속 주행 범위로 잡음, 사양 미정).
- 가속·감속은 높은 무게중심(경우 C 상단: 지면 위 약 3.23 m) 때문에 pitch를 흔든다. 준정적 어림으로 앞 롤러 바깥(x 0.901 m)에서 넘어지는 감속은 약 1.36 m/s²(가정 감속의 9배)다. 뒤 롤러는 정지 상태에서도 하중을 거의 잃는다(`dynamics_model.md` 3.8: 무게중심이 롤러 중심에서 0.437 m 앞, 핵심 거리 0.4165 m) → 롤러별 하중을 기록하고 판정은 dyn이 한다.

## 4. CAD에서 더 뽑을 것 (T0)

B-rep 캐시(`brep_cache.load_part("0:1:1:746")`, 3 s·약 1 GB)와 크롤러 파생 캐시, 면 색인(`face_index.query`)만 쓴다. STEP은 다시 읽지 않는다.

| 항목 | 방법 | 결과 키(제안) |
|---|---|---|
| 스프로킷 윤곽 | 링 단면(X = ±1045) 반지름 윤곽에서 이빨 끝·뿌리 반지름, 홈 원호 반지름·원호 중심 반지름(원 맞춤) | `sprocket.{num_teeth, addendum_radius, arc_radius, arc_centers_radius, assembly_radius}` |
| 스프로킷·아이들러·롤러 질량·관성 | 축 주변 동축 솔리드 묶음 `VolumeProperties`(강재 7.85, STEP 상위 재질), 축 기준 관성 | `*.mass_kg`, `*.inertia_kg_m2` |
| 아이들러 답면·플랜지, 롤러 답면·플랜지 | 원통 면 색인(축 기체 y, `convex=True`) | `idler.*`, `roller.*` |
| 슈 형상 | 피치 1개 솔리드 묶음: 슈 판·그라우저 끝(아래 향한 평면)·링크 레일 윗면(위 향한 평면)·부싱 원통 → 충돌 상자 3~5개 | `shoe.{pitch, height, boxes[], cylinder_radius}` |
| 슈 질량·관성 | 피치 1개 묶음(슈 판 2종 + 링크 2 + 핀 + 부싱 + 볼트군), 핀 축 기준 → 무게중심 기준 | `shoe.mass_kg`, `shoe.inertia_kg_m2` |
| 링크 핀 위치 | 핀 원통 축(`axis_point_*`)과 슈 무게중심의 상대 위치 | `shoe.pin_offset_m` |
| 트랙 길이 | 44 × 피치, CAD 다각형 둘레(7,667.3 mm)와의 차 원인(넓은 간격 위치) | `track.{num_shoes, length_m}` |
| 상부 런 형상 | ✅ 확인됨(2026-10-21, `upper_run_check.json`): 상부 런은 상부 롤러 꼭짓점에서 만나는 **직선 두 개**(처짐 0)로 그려져 있다(핀 중심 직선 맞춤: 뒤 9개 기울기 2.23°, 앞 8개 −1.87°, 잔차 최대 0.70 mm; 꼭짓점 핀이 끝 핀 현보다 46.0 mm 위, `pitch_line`). 상부 핀 높이 범위 46.6 mm는 처짐이나 배치 오차가 아니라 롤러 위로 꺾인 두 직선 때문이다. CAD에서 처짐·장력은 알 수 없다 | 장력은 가정(5절) |
| 주행 모터 하우징 | 앞 축 동축 솔리드·`SHELL 0:1:1:745` 치수 → 모터 크기 추정(배제량 추정에는 쓰지 않음) | 참고 |
| 질량 정리 | 섀시 = 상부체 + 다리 이동부 − 궤도 부품(2.4절), 합 검증 | `chassis.*` |

- **재사용**: 이 계획을 쓰는 동안 다른 작업이 `04_scripts/00_cad/derive_crawler_parts.py`로 크롤러 접촉 부품(롤러 6/측, 끝 슈·평탄 슈 피치 단위: 접지 슈 + 슈 판 + 링크 쌍 + 볼트 + 핀·부싱)을 부품별 B-rep(`01_cad/06_brep/derived/crawler/parts/`)과 색인으로 만들고 있다(2026-10-20 작업 트리에서 확인, 커밋 전). T0는 슈·롤러 질량·관성·형상을 이 결과에서 읽고, 스프로킷·아이들러·장력 장치만 새로 뽑는다(중복 추출 금지). 상부 롤러는 `04_scripts/00_cad/derive_crawler_upper_rollers.py`가 만든 `01_cad/06_brep/derived/crawler/crawler_upper_rollers.csv`(부품 22.5 kg, 로더 `brep_cache.load_crawler_upper_roller`, 회전부 17.16 kg·0.0368 kg·m²는 원통 절단 추정)와 `upper_run_check.json`을 재사용한다.
- 결과물: `01_cad/08_track/track_geometry.json`(출처 sha256·생성 스크립트·시각, `cache_manifest.json` 등록), 생성 스크립트 `04_scripts/00_cad/extract_track_geometry.py`, JSON 템플릿 생성기 `04_scripts/02_chrono/export_track_templates.py` → `02_params/track/*.json`(생성물). 경로는 제안이다.
- 이번 조사 스크립트(scratchpad, 프로젝트 밖): `probe_vehicle.py`(이름·상속), `probe_m113.py`(기능·비용), `shoes_csv.py`·`pins_csv.py`·`pin_radius.py`(슈 수·피치·핀 반지름), `sprocket_teeth.py`·`teeth2.py`(이빨 수). T0에서 프로젝트 스크립트로 다시 만든다.

## 5. 모르는 값과 가정

| 항목 | 지금 쓰는 값 | 근거·상태 | 영향 |
|---|---|---|---|
| 실기 하부체 = REXOME25 CAD | 같다고 가정 | STEP 설명, 제조사 확인 대기(CLAUDE.md) | 모든 치수 |
| 스프로킷 맞물림 | (a) 23이빨 반피치, $r_{eff}$ 317.0 mm | CAD 불일치(2.2절) | 주행 속도 4.3 % |
| 주행 모터 사양(배제량·감속비·릴리프·유량·2단 속도) | 모름. M1 이상 속도, 주행 0.3 m/s | 가정 | 필요 토크 판정 |
| 트랙 장력(아이들러 예압·스프링) | **가정**: 상부 런 경간마다 처짐 약 40 mm가 되는 장력. 현수선(포물선) 어림 $T\approx wL^2/8f$, $w$ = 57.5 kg/0.1732 m × 9.80665 m/s² ≈ 3.26 kN/m, $L$ ≈ 1.4 m(상부 롤러 1개가 상부 런을 끝 바퀴–롤러 경간 2개로 나눔, 축 간 1.400 / 1.405 m) → 약 **20 kN**(19.9 kN). 감도 처짐 20 / 60 mm(약 40 / 13 kN). 아이들러 장력 장치 힘은 위·아래 런 장력 합으로 약 2T(어림) | 상부 롤러 1개/측(CAD, 2026-10-21), CAD 상부 런은 직선 두 개(처짐 0)라 장력 정보 없음, 사양 없음 | 탈선·스프로킷 맞물림·주행 저항 |
| 슈–지면 μ | 0.5 | YAML `contact.crawler.friction`(가정) | 견인 한계 |
| 슈–바퀴·스프로킷 μ | 0.3 | 가정 | 주행 저항 |
| 롤러 수직 강성·감쇠 | 8.33×10⁶ N/m, 1.645×10⁴ N·s/m(롤러당) | YAML 크롤러 D안 값 / 12(가정, 근거 약함) | 정적 침하, heave 8.730 Hz(D안) |
| 슈 질량 | 약 57.5 kg/피치(강재) | CAD 부피 × 7.85(T0 확정) | 장력·처짐 |
| 스프로킷 회전부 관성(모터 회전부 포함 여부) | CAD 링+드럼+허브만 | 가정 | 가감속 토크(작음) |
| 주차 브레이크 토크 | 모터 $T_{max}$의 1.2배 | 가정 | 정지 유지 |
| 오거 위치 | 상단(레벨링 기본과 같음) | 사용자 확인 | pitch 응답 |
| 슈 핀 강성·감쇠 | 이상 조인트(무한 강성) | 템플릿 기본 | 부싱 옵션 시 Marder 예 3×10⁷ N/m 수준 가정 필요 |

## 6. 단계 계획 (T0~T4)

작업 시간은 로드맵 1절 기준(에이전트 구현·시험·판정 + 메인 세션 검토, 결정 대기 제외)이다. 계산 시간은 1.1절 실측에서 바디 수 비(약 0.77; 상부 롤러 2개를 더하면 0.79지만 단가는 그대로 둠)로 줄인 **추정 단가**를 쓴다: NSC PSOR 50 약 4.5 ms/스텝(한쪽 트랙만이면 약 2.5 ms), BB 100 약 12 ms, SMC LU 약 1.5 ms. Δt 5×10⁻⁴ s면 시뮬레이션 1 s당 2,000스텝, 1×10⁻⁴ s면 10,000스텝이다.

| 단계 | 목표 | 만드는 것 | 통과 기준 | 담당 | 작업 시간 | 계산 시간(직렬) |
|---|---|---|---|---|---|---|
| **T0** 가용성·CAD 추출 | 템플릿 값 전부를 CAD·YAML에서 만든다 | `extract_track_geometry.py` → `track_geometry.json`, `export_track_templates.py` → 생성 JSON, 질량 정리 | 슈 수·피치·트랙 길이 표, 이빨 수 재현(23), 섀시 + 궤도 부품 질량·무게중심 = YAML(상대차 ≤ 1×10⁻⁹), 관성 양정치·삼각부등식, 생성 JSON 왕복(로드 후 `GetPitch`·`GetNumTeeth`·`GetNumTrackShoes` 일치) | cad | 3~4시간 | 약 2분(B-rep 3 s + 단면·질량) |
| **T1** 한쪽 트랙 공회전 | 섀시를 공중에 고정(`SetFixed`), 한쪽 트랙을 M1으로 돌린다. 맞물림·장력·부호 확인 | `chrono/track/vehicle.py`(빌더), 부호 단위 시험, 장력 정착 | ① 핀 구속 위반 ≤ 1×10⁻⁴ m, 슈 간 거리 합 = 44 × 0.1732 m ± 0.1 mm(**둘레 보존**). ② 체인 평균 속도 = $\omega r_{eff}$ ± 1 %(다각형 효과 ±3.7 % 맥동은 평균에서 제외). ③ 30 s 탈선 없음(가이드·플랜지 접촉 유지), 이빨–부싱 접촉이 피치마다 1점. ④ 아이들러 장력 정착값 = 가정 예압 ± 5 %, 상부 런 처짐 기록. ⑤ 명령 +ω → 하부 런이 기체 −x로 이동(전진 방향) 부호 확정. ⑥ Δt 5×10⁻⁴/2.5×10⁻⁴/1×10⁻⁴ s에서 ②·④ 차 ≤ 1 % | cad → dyn | 4~6시간 | 30 s × 3 Δt: 5×10⁻⁴ s 약 2.5분, 2.5×10⁻⁴ s 약 5분, 1×10⁻⁴ s 약 12.5분(→ **메인 세션 권고**) |
| **T2** 양쪽 트랙 + 상부체, 평지 정적 | 섀시를 놓아 지면에서 정착 | 섀시 JSON, 지면 패치, 롤러 하중·슈 접촉력 기록기 | ① 지면 수직 반력 합 = 총중량 ± 1 %. ② 롤러별 하중 분포와 정적 침하가 L1 크롤러 D안 기준해(`06_analysis/00_dynamics/crawler_layout_check.json` D, 정착 자세 $u_z$·pitch)와 ±10 %(접촉 모델이 달라 허용을 넓힘, dyn 확정). ③ heave·pitch 진동수(초기 속도 가진)가 같은 파일의 크롤러 위 모드(D안 pitch 1.327 Hz, heave 8.730 Hz)와 ±10 %. ④ 브레이크 상태 10 s 수평 표류 < 1 mm(NSC 정지 마찰). ⑤ 질량 합(T0 재확인) | cad → dyn | 5~7시간 | 정착 10 s + 가진 2 × 5 s + 표류 10 s ≈ 30 s: 5×10⁻⁴ s 약 4.5분, 1×10⁻⁴ s 약 22분(→ 메인 세션 권고) |
| **T3** 전진·후진·정지 + GIF | 3.2절 시나리오, M1 기본, M2 감도 | `scenarios/drive.py`, 모터 모델 M1·M2, 기록(별도 `DriveRecord`), 측면도 GIF | ① 정속 구간 **미끄럼률** $s = 1 - v_x/(\omega r_{eff})$의 절댓값 ≤ 3 %(콘크리트, 가정 허용, dyn 확정). ② 이동 거리 = $\int v\,dt$ ± 1 %. ③ 정지 유지 3 s 뒤 정적 평형(T2 ①) 회복, 표류 < 1 mm. ④ 필요 토크 시계열 ≤ 가정 $T_{max}$, 최대 견인력 < μW. ⑤ 에너지 수지: 모터 일 = 운동 에너지 변화 + 소산(접촉·감쇠) ± 5 %(NSC 소산은 잔차로 계산, 경향만 판정). ⑥ 롤러 하중 ≥ 0 이탈 시각·크기 기록(전도 여유는 dyn) | cad (+py 그림 도구 필요 시) → dyn | 5~8시간 | 시나리오 4개(전진·후진 M1, 전진 M2, 전진-후진 GIF) ≈ 65 s: 5×10⁻⁴ s 약 10분, 1×10⁻⁴ s 약 49분(4병렬 약 13분, 1건 약 10~20분 → 메인 세션 권고) + GIF 렌더 약 5분 |
| **T4**(선택) SCM | 연약 지면 주행 | `SCMTerrain` 패치(이동 활성 영역), 침하·미끄럼 기록 | 침하·미끄럼률 기록, Janosi 전단 계수 감도. 판정 기준은 dyn이 SCM 파라미터 확보 뒤 정함 | cad → dyn | 6~10시간 + 파라미터 | SCM 2 cm 격자 약 3 ms/스텝(벤치마크, 영역 비례) + 궤도 4.5 ms → 약 8 ms/스텝: 13 s 주행 5×10⁻⁴ s 약 3.5분, 1×10⁻⁴ s 약 17분/건 |

- 합계: 작업 약 **17~25시간**(T4 제외, dyn 판정 단계당 약 1시간 포함하면 18~27시간), 계산 Δt 5×10⁻⁴ s 약 20분, 판정 Δt 1×10⁻⁴ s 약 1.5시간(직렬).
- 단가는 추정이다. **T0 끝에 우리 모델로 1 s 실측**해 이 표를 고친다(M113보다 질량비가 커 PSOR 반복이 늘 수 있음).
- 10분 넘는 단일 실행(1×10⁻⁴ s 판정 실행)은 에이전트가 띄우지 않고 명령 전체·예상 시간·출력 경로를 메인 세션 권고로 넘긴다(계획 문서 4절 장시간 규칙).

### 6.1 결과물

- `07_results/track_drive/<scenario>/<run_id>/`: npz(시각, 섀시 위치·자세·속도, 슈 88개 위치·자세, 스프로킷 각·각속도·토크, 아이들러 위치·장력, 롤러 하중 24개, 지면 접촉력 합·좌우·앞뒤, 슈 장력), `meta.json`(YAML·`track_geometry.json`·생성 JSON sha256, Δt, 솔버, pychrono 버전, 벽시계).
- 요약: `06_analysis/01_chrono/20_track_drive/track_drive_T<n>.json`.
- 그림: 측면도 GIF(궤도 감김, 슈 번호 색 하나 강조해 순환이 보이게, 지면·롤러·스프로킷·아이들러, 상부체 외곽) + 아래 패널 시계열(주행 속도 vs $\omega r_{eff}$, 미끄럼률, pitch·roll [°], 앞/뒤 롤러 하중 [kN], 스프로킷 토크 [kN·m]). matplotlib Agg(이 env에 VTK 없음). Irrlicht 창(`ChTrackedVehicleVisualSystemIrrlicht`)은 사용자가 원할 때만 띄운다.

## 7. 기존 로드맵과의 관계

| 항목 | 내용 |
|---|---|
| 선행 조건 | **S0 `make_system`**(R1 중력, R2 Bullet, 적분기)만 있으면 T0·T1을 시작할 수 있다. 다만 `make_system`은 지금 L1/L2b_NSC 모델만 받고 바닥 바디를 만든다 → 주행 모델용 선택지(`model="track_NSC"`, 바닥 없음, PSOR 50)를 더하는 작은 변경이 필요하다(공유 코드, 8절 위험 표). **S2b 크롤러 접촉(D안)** 결과는 T2 교차 기준(정적 침하·heave)으로 쓴다 — 없으면 dyn 기준해 `crawler_layout_check.json`만으로 판정한다. **S7 NSC**의 PSOR 경험(반복 수·반력 환산)이 T2 이후에 도움이 되지만 필수는 아니다 |
| 분리 | 별도 빌더(`chrono/track/`), 별도 시나리오(`scenarios/drive.py`), 별도 기록(`DriveRecord`, `signals.Record`를 바꾸지 않음), 별도 결과 폴더(`07_results/track_drive/`). 레벨링 모델의 크롤러 구 배열(R13)·지면 부싱(R15)·다리 모터는 쓰지 않는다 |
| 공유 | `params`(YAML 읽기), `frames`(좌표·쿼터니언 R10), `system.make_system`(확장), `record` 패턴(npz + meta, sha256), 크롤러 D안 강성·감쇠 키(롤러 강성으로 재사용), CAD 캐시(`06_brep`, `07_faces`) |
| 충돌 위험 | ① `make_system` 확장이 L1 기본 경로(SPARSE_LU + 잠금)를 바꾸면 안 된다 → 새 enum 값만 더하고 기존 시험 53건 재실행. ② YAML: 주행 파라미터를 지금 `export_params.py`에 넣지 않는다(다른 cad-expert가 수정 중). T0 결과는 `track_geometry.json` + 생성 JSON으로 두고, 나중에 `track_drive.*` 블록(ASSUMPTION 표시)을 `export_params.py`에 합칠지 메인 세션이 정한다. ③ CPU 경쟁: T3 판정 실행(직렬 약 49분)은 레벨링 S3·S7 장시간 실행과 겹치지 않게 메인 세션이 순서를 정한다. ④ 크롤러 질량(11,271 kg)과 롤러 강성 가정이 바뀌면(제조사 회신) 레벨링·주행 모두 재계산이다 |
| 순서 제안 | 레벨링 S0 마무리 → T0(CAD만, 레벨링과 독립) → S1~S2b와 병행 가능한 T1 → S2b 뒤 T2 → T3. 레벨링 트랙을 늦추지 않도록 T 단계는 메인 세션이 여유 있을 때 끼운다 |

## 8. 위험

| # | 위험 | 단계 | 대응 |
|---|---|---|---|
| 1 | 섀시(38.6 t) 대 슈(57.5 kg) 질량비가 커 PSOR 수렴이 나쁨(반력 합 오차, 핀 구속 위반) | T1~T3 | 반복 수 증가 → BB/APGD, 구속 위반·반력 합을 매 실행 기록 |
| 2 | 23이빨 반피치를 `SprocketSinglePin`이 처리 못 함(접촉 튐, 탈선) | T1 | 슈 원통 오프셋 조정 → 안 되면 12이빨 등가(b) |
| 3 | 상부 런(롤러 가운데 1개, 2026-10-21 CAD 확인으로 경간 약 1.4 m × 2)의 처짐·진동이 장력 가정에 민감 | T1 | 처짐 20/40/60 mm 감도, 필요하면 상부 롤러 가정 질문 |
| 4 | 롤러를 서스펜션 템플릿(암 + 비틀림 스프링)으로 근사 → 고주파 국부 모드(롤러 약 36 kg + 암, 약 70 Hz) | T1~T2 | Δt 수렴(T1 ⑥), 암 질량 작게 |
| 5 | 구동 부호·좌우 축 방향 혼동(조사에서 직관과 반대) | T1 | 부호 단위 시험(⑤) 통과 전 T2 금지 |
| 6 | 질량 이중 계산(크롤러가 상부체 YAML에 포함) | T0, T2 | 섀시 = 전체 − 궤도 부품, 합 자동 비교 |
| 7 | 주행 중 높은 무게중심 → 뒤 롤러 하중 상실·pitch 진동 | T3 | 롤러 하중 기록, 가감속 램프 완화, dyn 판정 |
| 8 | 비용 추정이 M113 실측의 비례 추정임 | 전부 | T0 끝 1 s 실측으로 표 갱신 |
| 9 | 실기 하부체가 CAD(REXOME25)와 다름 | 전부 | 제조사 확인 뒤 T0 재실행(생성기 구조라 값만 바뀜) |

## 9. 사용자 결정 필요

| # | 항목 | 마감 | 미정이면 |
|---|---|---|---|
| U1 | ~~스프로킷 전/후~~ | — | **해소: 앞쪽(사용자 확정 2026-10-20)**, CAD 근거 2.2절 |
| U2 | 스프로킷 맞물림 모델: (a) 23이빨 반피치($r_{eff}$ 317.0 mm) / (b) 12이빨 등가(330.8 mm) | T0 | (a), T1에서 실패하면 (b) |
| U3 | 주행 모터 사양(배제량, 감속비, 릴리프 압력, 유량, 1·2단 속도), 목표 주행 속도·가감속 | T3(M2) | M1 이상 속도, 0.3 m/s, 0.15 m/s² |
| U4 | 트랙 장력(아이들러 예압) 또는 허용 처짐 | T1 | 경간 1.4 m 처짐 40 mm 상당(약 20 kN), 감도 20/60 mm(약 40/13 kN) |
| U5 | 주행 시 오거 위치·마스트 자세(수직 유지 확인) | T2 | 상단, 마스트 수직 |
| U6 | Δt·솔버(판정 실행을 1×10⁻⁴ s 규칙으로 할지, 5×10⁻⁴ s로 할지) | T1 끝 | dyn 수렴 판정에 따름 |
| U7 | 상부 롤러 | T1 | ✅ CAD에 있음(측마다 1개, x 0.000 m, z −0.3327 m, 답면 Ø120, 2026-10-21). 회전부 질량·관성은 원통 절단 추정(17.16 kg·0.0368 kg·m², 가정) |
| U8 | 실기 하부체 = REXOME25 여부(제조사) | 언제든 | 같다고 가정 |

## 10. 연기 시험: Chrono 예제 궤도차량을 프로젝트 시스템에서 주행 (2026-10-20)

**우리 크롤러 모델이 아니다.** Chrono 예제 차량 템플릿(M113 단일 핀 JSON)의 사본을 고쳐, 프로젝트 `make_system`이 만든 시스템에 넣고 스프로킷 토크로 전진·후진시킨 API 연기 시험이다. 물리 판정(정적 평형·미끄럼률·에너지)은 하지 않았다.

- 스크립트: `04_scripts/02_chrono/track_drive/smoke_drive_gif.py`(ruff check·format 통과)
- 결과: GIF `06_analysis/01_chrono/20_track_drive/track_drive_smoke.gif`(git 제외, 1100×740 px, 126프레임, 60 ms/프레임, 약 2.1 MB), 요약 `06_analysis/01_chrono/20_track_drive/track_drive_smoke.json`(추적). 고친 JSON 사본과 프레임 PNG는 `07_results/track_drive_smoke/`(git 제외)에 실행 때 만든다. pychrono 설치 폴더의 원본 데이터는 고치지 않는다.
- 재생성(프로젝트 루트, 약 1분):

```powershell
& C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -u 04_scripts/02_chrono/track_drive/smoke_drive_gif.py
```

| 항목 | 값 |
|---|---|
| 시스템 | `make_system(params, "L2b_NSC", dt=5e-4, floor_plate=False)` → `ChSystemNSC`, 중력 (0, 0, −9.80665) m/s²(YAML, R1), Bullet(R2), PSOR 50회(YAML `contact.rigid_floor.L2b_NSC.solver*`) |
| 차량 데이터 | Chrono `data/vehicle/M113` JSON 사본. 슈 피치 0.154 → **0.1732 m**(REXOME CAD 피치), 원통 오프셋·가이드 핀·충돌 상자 길이 ×k(k = 1.1247), 스프로킷 이빨 10 → **11**, 조립·이끝·원호 중심 반지름 ×s(s = 1.2336, 조립 반지름 0.3022 m), 원호 반지름 ×k, 슈 수 63/64 → 58/59(57/58이면 Chrono가 "Insufficient number of track shoes, Missing distance 0.116 m" 경고를 낸다. 예외가 아니라 경고라 놓치기 쉽다), 슈 질량·관성은 M113 값 그대로. 로드휠 5개/측, 상부 롤러 없음 |
| 지면 | `RigidTerrain` 평면 z = 0, NSC μ 0.8(M113 예제 값, REXOME 가정 아님) |
| 구동 | `DisconnectDriveline()` 뒤 매 스텝 `ChSprocket.ApplyAxleTorque(T)`, 스프로킷당 \|T\| = 4,000 N·m. 0~0.5 s 토크 0(초기 높이 1.1 m에서 낙하·착지 포함), 0.5~1.5 s 전진 토크, 1.5~2.5 s 역토크 |
| 부호(실측, 0.3 s 사전 실행) | **`ApplyAxleTorque(+T)` → +x 진행**. 이때 `GetAxleSpeed()`는 **음수**, 기어 바디의 전역 각속도 ω_y는 양수다(ω_y > 0이면 하부 런이 −x로 움직여 차체가 +x로 감). 1.1절 조사(−T → −x)와 같은 규약이다 |
| 비용 | 5,000스텝 27.8 s, **5.6 ms/스텝**(PSOR 50, 기록 포함; `track_drive_smoke.json` `model.wall_s` 27.84, `model.ms_per_step` 5.57. GIF 렌더 포함 전체 `wall_total_s` 54.5 s) |
| 결과(차체 무게중심) | 1.5 s(전진 끝): 이동 +0.552 m, vx +1.160 m/s. 1.0~1.5 s 평균: vx 0.888 m/s, ω_y r_eff 0.814 m/s(r_eff = N p / 2π = 0.3032 m), 평균끼리의 미끄럼 −0.083(차체가 체인 속도보다 빠름). 2.5 s: 이동 +0.445 m, vx −0.953 m/s(후진 중), 미끄럼 −0.002 |
| GIF 표시 | 왼쪽 트랙 측면도(슈 58개, 슈 0번 주황, 스프로킷 11이빨 윤곽, 아이들러 초록, 로드휠, 바퀴 회전 표시선, 차체 외곽은 개략도, 무게중심 +), 지면 눈금. 시계열(vx, ω_y r_eff)과 시각·구간·T·`GetAxleSpeed`·ω_y·x·vx·미끄럼·부호 함정 문구 |

관찰(판정 아님):
- 전진 가속 구간 미끄럼이 음수(−8 %)다. 다각형 효과, 11이빨 윤곽을 비례로 늘린 형상, 착지 직후 남은 진동, 차체 pitch가 섞인 값이다. T1에서 실제 템플릿으로 다시 본다.
- 착지 뒤(약 0.3 s) 체인 속도 신호가 크게 흔들린다(±2 m/s 순간값). 스프로킷이 공중에서 자유 회전하다 착지한 영향이다.
- 사전 부호 실행의 vx가 두 번 실행에서 0.318 / 0.326 m/s로 조금 달랐다. 본 시나리오 체크포인트는 두 실행에서 같았다. 원인(PSOR·Bullet 순서)은 확인하지 않았다.
