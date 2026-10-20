# CLAUDE.md

아우트리거 4개로 상부체의 자세를 제어하는 **시뮬레이션** 프로젝트다. 개요와 폴더 구조는 [README.md](README.md), 전체 로드맵·지금 위치는 [00_docs/00_roadmap.md](00_docs/00_roadmap.md)를 본다. 단계 항목을 끝내거나 결정이 생기면 로드맵 1·4·5절을 갱신한다(체크 상태 원본은 계획 문서).

## 확정 사항 (2026-10-19)

- 대상은 시뮬레이션뿐이다. 하드웨어 드라이버, 통신, 실시간 제약은 범위 밖이다.
- 언어는 Python이다.
- 구동기: 실물은 유압 실린더다. 시뮬레이션에서는 목적에 맞게 단순화한 모델(예: 속도·스트로크 제한이 있는 1차 지연)로 바꿔도 된다. 바꿀 때는 무엇을 단순화했는지 `00_docs/`에 적는다.
- 자세 센서는 IMU다. 노이즈·바이어스·지연 같은 센서 모델은 제어기와 분리한다.
- 물리 엔진은 Project Chrono(PyChrono)다. 실행 환경은 conda `Chrono-dev`다(Python 3.12, 패키지와 용도는 [environment.yml](environment.yml)).
  - 실행: `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe`
  - 같은 환경에 MuJoCo(`mujoco-python`), STEP 처리(`pythonocc-core`, `trimesh`), 제어 설계(`control`)가 있다. 모두 conda로 설치했다. 패키지를 더할 때도 conda에 있으면 conda를 먼저 쓴다.
  - `pychrono.sensor`에 가속도·자이로 센서(`ChAccelerometerSensor`, `ChGyroscopeSensor`)가 있지만, IMU 모델은 엔진 독립으로 직접 구현한다.
  - ML/DL 학습은 별도 환경 `pytorch_214_cuda_python_313`(Python 3.13, PyTorch 2.14.1+cu130, scikit-learn, LightGBM, ONNX; 정의 [environment-ml.yml](environment-ml.yml))에서 한다. 실행: `C:\ProgramData\miniforge3\envs\pytorch_214_cuda_python_313\python.exe`. GPU RTX 4070 SUPER(12 GB). 이 환경의 numpy BLAS는 **MKL + TBB 스레딩 계층**이다. torch를 먼저 import한 뒤 MKL 기본 계층이면 numpy 행렬곱에서 프로세스가 죽으므로(0xC06D007F), `MKL_THREADING_LAYER=TBB`를 conda 환경 변수와 site-packages의 `sitecustomize.py` 두 곳에 걸어 `python.exe` 직접 호출에서도 적용되게 했다(환경을 다시 만들면 `sitecustomize.py`도 다시 만든다 — environment-ml.yml 주석). 학습 데이터는 Chrono-dev가 만든 npz를 읽고, 시뮬레이션 안 추론이 필요하면 ONNX로 내보낸다.
  - 시각화는 `pychrono.irrlicht`를 쓴다. VSG 시각화 모듈은 `pychrono.vsg3d`라는 이름으로 있지만(2026-10-19 import 확인) 쓰지 않는다.
  - Chrono 9 이후로는 충돌 시스템을 지정해야 접촉이 생긴다: `sys.SetCollisionSystemType(chrono.ChCollisionSystem.Type_BULLET)`.
- 지면 모델은 두 가지를 지원한다.
  - 강체 지면(예: 시멘트 바닥): Chrono 접촉(SMC/NSC)
  - 연약 지면(단단한 토양): `SCMTerrain`(Bekker-Wong). 패드 침하로 자세가 흐트러지는 상황을 다룬다.
- 구동기는 `ChLinkMotorLinear` 계열로 유압 실린더를 근사한다.
  - 최대 스트로크 680 mm (CAD 추정값 보어 700 − 피스톤 20과 같음).
  - 0 mm에서 최대 스트로크까지 30 s. 최대 신장·수축 속도 = 680/30 ≈ 22.7 mm/s.
- 아우트리거는 크롤러까지 들어 올린다. 따라서 상부체(자세 제어 대상)에는 크롤러가 포함된다.
- 기준 질량(잠정, 2026-10-19): **오거 공구만 강재(7.85 g/cm³), 나머지는 STEP 밀도**. 이 기준을 "경우 C"라 부른다. 실제 운용 중량이 나오면 바꾼다. (경우 A = STEP 밀도 그대로, 경우 B = '일반' 재질 전부 강재·유리 2.5는 비교용으로만 남긴다.) 질량 감사(2026-10-20, `00_docs/00_cad/cad_origin_mass_imu.md` 2절): 그려진 질량은 신뢰할 만하나 엔진·작동유·연료·펌프 등이 모델에 없어 운용 중량으로는 과소일 가능성이 크다. **운용 중량을 확인할 때까지 경우 C(38,556 kg)를 유지한다**(사용자 결정 2026-10-20).
- 시나리오 (2026-10-19 재정립): 자세(roll·pitch) 제어는 **마스트를 수직으로 세운 상태**에서만 한다.
  - 오거 위치는 마스트를 따라 3단계다: 상단, 중단, 하단. 오거 위치마다 상부체 무게중심·관성이 달라진다. 상세는 [00_docs/00_cad/cad_auger_levels.md](00_docs/00_cad/cad_auger_levels.md), 값은 `01_cad/03_auger/auger_levels.json`.
    - 이동 부품: 구동부(`DRIVE AUGER ASSY`)와 오거 공구(`AUGER TOOL`)가 한 덩어리로 마스트 축(기체 z)을 따라 평행이동한다.
    - 위치(CAD 자세 대비 이동량 Δ, 위쪽 +): 상단 +2.996 m(구동부 모터 가드가 탑시브 프레임에 닿는 한계), 하단 −5.602 m(구동부 프레임이 하부 가이드 베이스에 닿는 기구 한계), 중단 −1.303 m(상·하단의 중간). CAD 위치(Δ 0)는 범위의 65 %다.
    - 오거 공구 질량은 강재로 가정한다(약 1,420 kg, STEP 재질은 '일반' 자리표시 값).
    - 하단에서 공구 끝이 지면 아래로 들어가도 천공 반력·토크는 넣지 않는다. 오거 위치는 질량 분포만 바꾼다.
    - 기본 실행 단계는 **상단**이다(무게중심이 가장 높아 제어가 가장 어려운 경우). 제어기 검증은 세 단계 모두 한다.
- 다리 기하 (2026-10-19):
  - 네 다리 모두 신장량 0~680 mm로 통일한다. CAD에서 후방 피스톤이 2 mm 덜 수축돼 있으므로, 후방 패드를 2 mm 올린 위치를 완전 수축(0 mm)으로 둔다.
  - 패드는 CAD 형상·방향 그대로 쓴다(팔각, 면적 0.1071 m², 전방 47.1°·후방 3.4° 회전).
  - 패드와 로드는 **구면(스위블) 조인트**로 잇는다. CAD는 강결합이지만 강결합이면 지면과 0.13°만 어긋나도 모서리 접촉이 된다.
- 센서 (2026-10-19): IMU + 실린더 압력(다리 하중) + 스트로크(신장량). 비틀림 성분(하중만 옮기고 자세는 그대로)은 IMU로 보이지 않으므로 접지 유지는 압력으로 판단한다.
- 접지 판정 최소 하중 F_min = 다리당 평균 하중의 10 % = 9.453 kN, **실린더 힘(압력 센서로 재는 값) 기준**이다(패드 접촉력으로는 로드 무게가 더해져 10.50 kN). 제어 중 모든 다리가 F_min 이상을 지킨다.
- 구동기 운용안 **B** (2026-10-19, [00_docs/01_dynamics/actuator_L2_feasibility.md](00_docs/01_dynamics/actuator_L2_feasibility.md)): 제어기 개발은 **L1**, 큰 경사·실 마찰 감도(F_s 0/2/5/12 kN)·연약 지면(SCM) 재판정은 **L2b**(L2 + 횡 부싱)로 병행한다. L2는 L1과 같은 근거 없는 가정에 묶여 하중 신뢰도가 오르지 않으므로 기본으로 바꾸지 않는다.
- Chrono 10 SMC 접촉에는 **정지 마찰(stick)이 없다**(경사 블록 시험으로 확인, [00_docs/03_chrono/chrono_stick_friction_test.md](00_docs/03_chrono/chrono_stick_friction_test.md)). MultiStep은 OneStep과 비트 단위로 같고, 2°에서 0.11 m/s로 미끄러진다. 그래서:
  - L1: 패드마다 지면 고정 `ChLoadBodyBodyBushingSpherical`(접선 kt) + 매 스텝 원형 Coulomb 항복 처리(Python, `SetApplicationFrameB`로 고정점 이동). 내장 `ChLoadBodyBodyBushingPlastic`은 미끄럼 구간이 틀려 쓰지 않는다.
  - L2b: `ChSystemNSC` 접촉(PSOR). 접선 유연성은 횡 부싱이 맡는다.
  - Chrono 함정: Hooke `gn`·`gt`는 유효 질량당 값이라 고정 바닥 바디의 질량을 크게(예: 1e9 kg) 둬야 감쇠가 산다. 부싱 감쇠는 입력의 2배로 작용하므로 ct/2를 넣는다. `GetPos()`는 참조를 돌려주므로 저장할 때 복사한다.
- 구동기 모델: 유압 사양을 아직 몰라 **L1을 임시 기본**으로 쓴다(2026-10-19). L1 = 강체 위치 모터(속도 ±22.67 mm/s 제한) + 유압유·접촉 직렬 유연성을 패드 접촉 강성에 합침(가정치, 약 2.1×10⁷ N/m). 유압 사양이 나오면 **L2**(`ChLinkMotorLinearForce` + 유압유 기둥 강성·감쇠 힘 법칙)로 바꾼다.
  - 유압 회로(사용자 제공 회로도, 해석은 [00_docs/02_hydraulic/hydraulic_circuit.md](00_docs/02_hydraulic/hydraulic_circuit.md)): **복동 실린더 + 실린더 직결 이중 파일럿 체크**(헤드·로드측 모두 잠김, 호스는 잠긴 체적 밖), 비례 방향 밸브 4섹션(압력 보상형으로 보임), 최고 압력 210 bar(다리당 최대 218 kN), 펌프 60.2 L/min(네 다리 동시 22.67 mm/s 신장에 56.5 L/min 필요 — 일치).
  - 압력 한계(사용자 설명, 2026-10-19): **이동 중 210 bar**(MCV 릴리프, 행정 끝에서만 도달) → 구동기 힘 포화 218 kN(신장)/18.6 kN(수축). **잠긴 정지 상태 최대 350 bar**(실린더 최대 부하 시험 압력, 외력 진동·굴착 뒤틀림으로 발생 가능) → 364 kN. 350 bar 초과 우려 시 제조사는 파일럿 체크를 카운터 밸런스 밸브로 교체할 계획(350 bar 이상 내부 부하 차단, 순간 충격은 제외).
  - 압력 센서는 ① 로크 밸브 블록에 있어 정지 중 갇힌 부하 압력을 계속 읽는다. 제어 판정: 모든 다리 실린더 힘 ≥ F_min, 그리고 잠긴 상태 압력 ≤ 350 bar.
  - 접지 판정(2026-10-20): 압력 절대값은 실 마찰(±F_s) 때문에 부상을 놓칠 수 있다(F_s 12 kN에서 부상 순간 압력 판독 10.9 kN > F_min). 그래서 **압력·스트로크·자세(IMU)를 결합해 판정**한다. **물리 기반 판정기를 먼저** 만들고(증분 강성 Δp/Δs, 자세 반응과 기구학 J의 일치, 마찰 이력 띠), **ML/DL은 비교 후보**로 시뮬레이션 데이터(Chrono 접촉력 = 라벨, F_s·β·경사·오거·노이즈 무작위화)로 학습해 물리 기반과 비교한다. 제어기가 레벨링 중·후에 다리를 수 mm 움직여 보는 **확인 동작(탐침)을 허용**한다(자세 변화는 ±0.1° 안).
  - 로크 밸브 모델(2026-10-19): **파일럿 체크 기본**, 카운터 밸런스(350 bar에서 다리가 밀리는 릴리프 동작)는 L2b 비교 옵션.
  - 350 bar 판정용 외란은 **D2 수직 하향 외력**(오거 인발·걸림, 마스트 축에 하향 계단/램프 힘)만 범위에 넣는다. 크기·작용 시간은 미정. 레벨링 시나리오 자체에는 여전히 천공 반력·토크를 넣지 않는다. 외란 후보 D1~D5는 [00_docs/01_dynamics/dynamics_model.md](00_docs/01_dynamics/dynamics_model.md) 5.1절.
  - 유압유 유효 체적 탄성계수 β_eff = **1.0 GPa**(사용자 결정, 2026-10-19). 조사 권장 중앙값 1.3 GPa(0.9~1.6)보다 낮게 둔 가정이며, 감도 해석은 0.69~1.6 GPa로 한다. 근거는 [00_docs/02_hydraulic/hydraulic_fluid_survey.md](00_docs/02_hydraulic/hydraulic_fluid_survey.md). 강체 모터 + 콘크리트 접촉만(R1)은 하중 평가에 쓰지 않는다(하중 민감도 약 15배 과대). 상세는 [00_docs/01_dynamics/dynamics_model.md](00_docs/01_dynamics/dynamics_model.md).
  - 감쇠비(사용자 결정, 2026-10-20, 근거 [00_docs/01_dynamics/damping_survey.md](00_docs/01_dynamics/damping_survey.md)): **다리 축(잠긴 실린더) ζ 0.03**(감도 0.01~0.10), 이동 중(L2 밸브 구동) ζ 0.10, **크롤러 접지 콘크리트 0.05 / 토양 0.2**(감도 0.02~0.3), 구조·마스트 0.015. 다리 감쇠계수는 **상하(heave) 모드 약 7.4 Hz** 기준으로 맞춘다(로킹 1.8 Hz는 약 0.007로 더 작아짐, 보수적). 실 마찰 F_s는 점성 감쇠에 섞지 않고 따로 모델링한다. 모두 문헌 기반 추론값이다(실측 없음). Chrono SMC Hooke의 `gn`은 접촉 두 바디(패드·바닥)의 유효 질량 기준이라, 상부체 모드 ζ를 주려면 c를 직접 계산해 넣는다.
  - 마스트를 눕힌 자세(운송 자세)는 고려하지 않는다. [00_docs/00_cad/cad_mast_review.md](00_docs/00_cad/cad_mast_review.md)는 참고 자료로만 남긴다.
- 상부체 질량, 무게중심, 관성, 다리 부착 위치는 CAD를 검토한 뒤 확정한다. 확정 전에 쓰는 값은 가정치로 표시한다. CAD 검토 결과는 [00_docs/00_cad/cad_review.md](00_docs/00_cad/cad_review.md)(제원·다리). [00_docs/00_cad/cad_mast_review.md](00_docs/00_cad/cad_mast_review.md)(마스트 힌지·눕힌 자세)는 시나리오에서 빠져 참고용이다.
- 제어 성능 목표는 roll·pitch 목표값에 대한 자세 정확도다. 정상상태 오차 허용치는 **±0.2°**다(2026-10-20 ±0.1°에서 완화, 근거 [00_docs/05_sensors/imu_cabin_and_accuracy_review.md](00_docs/05_sensors/imu_cabin_and_accuracy_review.md)). 완료 판정 데드밴드는 0.03°를 유지하고, **IMU 현장 영점 교정을 운용 절차로 의무화**한다. **장착 몫 0.02°**(사용자 결정 2026-10-20: IMU를 C1 프레임에 직접 달아 캐빈 방진 마운트 몫 0.02°를 빼고 0.03° → 0.02°. 핀 러그 무하중이 제조사 확인되면 0.01°까지 줄일 수 있다, 근거 `00_docs/05_sensors/imu_cabin_and_accuracy_review.md` 10절). 그래서 센서 정지 영점 오차 허용은 **0.14°(2.44 mg)**다(이전 0.13°, 2.27 mg).
- IMU 장착 위치(2026-10-20): **캐빈 바닥 아래 상부 프레임**, 기체 좌표 **(0.31, 0.88, 0.040) m**(BASE DECK 좌측 폰툰 15 mm 가로판 윗면, 후보 C1; 사용자 결정 2026-10-20, 근거 `00_docs/00_cad/cad_origin_mass_imu.md` 4절, 그림 `01_cad/01_parts/imu_c1_*.png`). 박스 100×100×50 mm가 간섭 없이 들어가며, 판 후방 가장자리 여유가 20 mm라 설치 때 전방으로 조금 옮기는 편이 낫다. 이전 가정점 (0.20, 0.88, 0.30) m는 폰툰 안 빈 공간이라 붙일 면이 없었다. 캐빈 몸체에 달지 않는다(캐빈 방진 마운트 오차 회피). 로킹 회전 중심이 지면 아래라 **IMU를 높이 달수록 겉보기 기울기 증폭이 커진다** — 낮게 단다.
- 시뮬레이션 시간 간격(사용자 결정, 2026-10-20) — **용도별 dt**:
  - 일반 실행(제어기 개발, 감도 해석, ML 데이터 생성): L1·L2b 약 **1×10⁻⁴ s**. 적분기 `EULER_IMPLICIT_LINEARIZED`의 수치 감쇠 ζ_num ≈ ωΔt/2를 1차 로킹 모드 물리 감쇠의 10 % 이하로 두는 규칙값이다(감쇠비 개정으로 0.2 ms에서 줄어듦, 값은 `02_params/rexome33.yaml` `simulation.*.dt_s`).
  - 기준해(V9 수렴 판정)와 접지 전환 해석(V4 들어 올림, 다리 부상·재접지, D2 외란 하중 피크): **1×10⁻⁵ s**. 한 실행 안에서 전환 구간만 작은 dt로 바꾸는 방식도 허용한다.
  - L2(유압 사양 확정 후)는 로드 국부 모드 규칙값(현재 5×10⁻⁵ s)을 따른다.
- 선형 솔버(사용자 결정, 2026-10-20): L1(SMC) 기본은 **SPARSE_LU + 희소 패턴 고정**(`LockSparsityPattern(True)`). 근거는 `06_analysis/01_chrono/solver_benchmark.json`(전체 규모 L1에서 QR 147 / LU 133 / Pardiso 447 µs/step, 결과 동일, 미지수 180 이상에서 QR 급증). SPARSE_QR·PARDISO_MKL은 옵션으로 둔다. PARDISO_MKL은 env 미활성 실행에서 `Library\bin\libomp.dll`을 미리 로드해야 동작한다(`chrono/system.py`가 처리). L2b(NSC)는 PSOR 50회.
- 자세 신호 필터: **2차 저역통과**(1차 τ 0.5 s × 2단). 1차 필터는 로킹 잔류 0.023°가 남아 부족하다.
- 제어 구조(잠정, 2026-10-20): **C2 = 기구학 분해(heave·roll·pitch) + 압력 기반 비틀림 루프(n^T P → 0) + F_min 가드**, 레벨링 뒤 **결합 접지 판정(탐침)**. 다리 속도 u = A[ż, φ̇, θ̇]ᵀ + n·τ̇, n = (0.476, −0.476, −0.523, 0.523). 대안은 C8(2상). 비교 근거는 [00_docs/04_control/control_candidates_comparison.md](00_docs/04_control/control_candidates_comparison.md), 문헌은 [00_docs/04_control/leveling_control_survey.md](00_docs/04_control/leveling_control_survey.md).

## 도메인 용어

| 용어 | 뜻 |
|---|---|
| 상부체 | 아우트리거 4개가 받치는 구조물. 자세 제어 대상인 강체 |
| 아우트리거 (leg) | 상부체를 지면에 지지하는 다리 4개. 신장 길이를 제어한다 |
| 레벨링 | 상부체 roll·pitch를 목표값(보통 0)으로 맞추는 동작 |
| 접지 / 부상 | 다리가 지면 반력을 받는 상태 / 반력이 0이 되어 뜬 상태 |

## 설계상 주의

- 4점 지지는 부정정이다. 3개의 다리만으로 자세가 정해지므로, 남은 다리는 자세가 아니라 하중 분배를 결정한다. 제어 목표에 "모든 다리 접지 유지"(반력 > 0)를 포함한다.
- 다리 이름과 좌표계는 아래 정의를 따른다. 바꿀 때는 이 표를 먼저 고친다.

## 좌표계와 명명

- 기체 좌표계: x 전방, y 좌측, z 상방 (오른손 좌표계). roll은 x축, pitch는 y축 회전이다.
- 전방은 마스트와 `FRONT JACK CYL`이 있는 쪽이다 (2026-10-19 사용자 확정).
- CAD 축 대응: x = +Z_cad, y = +X_cad, z = +Y_cad (CAD는 Y-상방, 길이 mm). 회전행렬(기체 ← CAD) `[[0,0,1],[1,0,0],[0,1,0]]`.
- 다리 순서: `FL`(전방 좌), `FR`(전방 우), `RL`(후방 좌), `RR`(후방 우). 배열 인덱스는 이 순서로 0–3이다.
  - CAD 대응: FL = `FRONT JACK CYL:1`, FR = `FRONT JACK CYL:2`, RL = `REAR JACK CYL:1`, RR = `REAR JACK CYL:2`.
  - `cad_summary.json`의 패드 z 값은 패드 **바닥면** 높이다 (질량 중심 아님).
- 기체 좌표 원점: CAD 원점 = 선회 링(크롤러 장착 링) 볼트원 PCD 1,120 mm 중심축 ∩ 데크 하면(사용자 결정 2026-10-20, 근거 `00_docs/00_cad/cad_origin_mass_imu.md` 1절). 지면(크롤러 바닥) z = −1.0509 m.
- 단위는 SI(m, kg, s, rad)다. 각도는 표시할 때만 도(°)로 바꾼다.

## 미정 사항

- 상부체 실제 질량·무게중심·관성 (운용 중량, 엔진·작동유·연료, 운전실·오거 공구·크롤러 실제 질량)
- 연약 지면 SCM 파라미터 (Bekker kc·kφ·n, 응집력, 내부마찰각, Janosi 전단 계수)
- roll·pitch 목표값 범위
- 제어기 세부: 탐침을 매번 할지(감시 트리거 때만 할지), 비틀림 목표(n^T P = 0 또는 최소 하중 최대화), 실 마찰 설계 띠 F_band, 게인 — 근거는 [00_docs/04_control/control_candidates_comparison.md](00_docs/04_control/control_candidates_comparison.md) 8절
- 유압 사양(체적 탄성계수, 배관, 응답 시정수), 접촉 강성·감쇠·마찰 실측값 — 지금은 가정치
- 마스트 1차 굽힘 진동수(L1 로킹 1.8~3.9 Hz와 겹칠 수 있음)
- IMU 센서 모델 선정, 제어 주기(기본 20 ms 가정). 장착점 C1의 실기 확인(점검구 접근, 판 국부 강성)

## 작업 규칙

- 시뮬레이션 공통 파라미터의 단일 출처는 `02_params/rexome33.yaml`이다. Chrono·MuJoCo 모델은 모두 이 파일을 읽는다. 생성물이므로 손으로 고치지 않고 `04_scripts/00_cad/export_params.py`로 다시 만든다. 블록마다 출처 주석이 있고 가정은 `ASSUMPTION`으로 표시돼 있다.
- CAD 원본(`*.stp`)은 약 630 MB라 git에서 제외한다. 읽을 때는 파일 전체를 열지 말고 `grep -a`로 필요한 엔티티만 뽑는다. 한글 부품명은 STEP `\X2\…\X0\`(UCS-2 hex)로 인코딩돼 있다.
- CAD 자동 추출(부품 표, 부피·무게중심·관성)은 `Chrono-dev`의 pythonocc-core로 한다.
- FreeCAD 1.1.4가 `C:\Program Files\FreeCAD 1.1\bin`에 있다. 필요할 때 참고용으로 쓴다.
  - 용도: 다리·상부체 후보를 눈으로 확인, 치수 측정, 메시 내보내기 결과 점검. 자동 추출 결과와 대조하는 교차 검증.
  - GUI: `freecad.exe`. 헤드리스 스크립트: `freecadcmd.exe script.py`. FreeCAD에 딸린 `python.exe`(3.11)는 `Chrono-dev`와 별개다.
  - FreeCAD를 `Chrono-dev`에 conda로 설치하지 않는다. OpenCASCADE 버전이 부딪힐 수 있다.
  - 630 MB STEP을 열면 수 분 이상 걸리고 메모리를 많이 쓴다. 필요한 부품만 따로 내보내 확인하는 편이 낫다.
- CAD 추출(부품 표·질량 특성)·형상 변환·Chrono 모델·시뮬레이션 스크립트는 cad-expert 에이전트에, 그 밖의 Python 코드(제어기, IMU 모델, 데이터 처리) 작성·수정은 python-expert 에이전트에 맡긴다.
- 동역학 해석(운동방정식·선형화, 4점 지지 부정정 하중 분배, 고유진동수, 적분기·시간 간격 선택, 시뮬레이션 결과의 물리 타당성 판정, 제어 관점 상태공간·LQR)은 dynamics-expert 에이전트에 맡긴다. 기준 환경은 conda `dynamics-dev`다. Chrono 모델을 만들거나 바꿀 때는 dynamics-expert의 검증 기준(`00_docs/01_dynamics/dynamics_model.md`)으로 결과를 판정한다.
