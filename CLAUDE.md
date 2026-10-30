# CLAUDE.md

아우트리거 4개로 상부체의 자세(roll·pitch)를 제어하는 **시뮬레이션** 프로젝트다.

| 알고 싶은 것 | 원본 |
|---|---|
| 개요·폴더 구조 | [README.md](README.md) |
| 지금 단계·체크리스트·다음 할 일 | [00_docs/00_roadmap.md](00_docs/00_roadmap.md) 1절(진행)·4절(체크)·6절(다음) |
| 숫자 파라미터(단일 출처) | `02_params/rexome33.yaml`(생성물, 손으로 고치지 않음) |
| 결정 이력·근거(U-*, Q-*, 재실행 판정) | [00_docs/decision_log.md](00_docs/decision_log.md) |
| 제어기 명세·판정 | `00_docs/04_control/s6_control_spec.md` |
| 동역학 모델·검증 기준 | `00_docs/01_dynamics/dynamics_model.md` |

- 이 파일에는 **지침과 현재 기준값만** 둔다. 결정 경과·판정 수치는 decision_log와 스펙 문서에 쓰고, 여기에는 바뀐 기준값만 고친다.
- 단계 항목을 끝내거나 결정이 생기면 로드맵 1절(진행 수)·4절(체크)·5절(결정)을 갱신한다(체크 상태 원본은 계획 문서).
- 기준값 표의 값과 YAML이 다르면 YAML이 맞다(YAML에 없는 센서 주기·제어기 값은 표의 원본 칸 코드·명세가 맞다). 다름을 발견하면 보고한다.

## 범위

- 대상은 시뮬레이션뿐이다. 하드웨어 드라이버, 통신, 실시간 제약은 범위 밖이다. 언어는 Python이다.
- 구동기 실물은 유압 실린더다. 목적에 맞게 단순화해도 되며, 단순화한 내용은 `00_docs/`에 적는다.
- 자세 센서는 IMU다. 센서 모델(노이즈·바이어스·지연)은 제어기와 분리하고 엔진 독립으로 직접 구현한다(`pychrono.sensor`는 쓰지 않음).
- 자세 제어는 **마스트를 수직으로 세운 상태**에서만 한다. 운송 자세(마스트 눕힘)는 다루지 않는다.
- 레벨링 목표는 **데크(상부체) 수평**이다. 마스트 처짐에 따른 경사는 기록만 한다.
- 아우트리거는 크롤러까지 들어 올린다. 상부체(제어 대상)에는 크롤러가 포함된다.
- 오거 위치는 질량 분포만 바꾼다. 천공 반력·토크는 넣지 않는다.
- **작업 우선순위**(사용자 방침 2026-10-24): roll·pitch 자세 제어에 직접 필요한 일을 먼저 한다. D2 외력, 제조사 확인 질문, 체크 밸브 고압 거동 등은 나중에 확인한다(D2는 정적 한계 표만 두고 보류).

## 실행 환경

| env | 실행 | 용도 |
|---|---|---|
| `Chrono-dev` (Py 3.12) | `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe` | PyChrono 10 시뮬레이션, CAD 추출(pythonocc-core, trimesh), MuJoCo, control, PyVista 0.49.1(pip), ffmpeg, psutil. 정의 [environment.yml](environment.yml) |
| `pytorch_214_cuda_python_313` (Py 3.13) | `...\envs\pytorch_214_cuda_python_313\python.exe` | ML/DL 학습(PyTorch 2.14.1+cu130, scikit-learn, LightGBM, ONNX, optuna, shap, imbalanced-learn). 정의 [environment-ml.yml](environment-ml.yml). GPU RTX 4070 SUPER 12 GB |
| `dynamics-dev` | `conda run -n dynamics-dev python -I` | 동역학·제어 해석(dynamics-expert, control-expert). 정의 [environment-dynamics.yml](environment-dynamics.yml) |
| `hydraulics-dev` (Py 3.13) | `conda run -n hydraulics-dev python -I` | 유압 해석(hydraulics-expert), Hopsan 2.24.4, OpenModelica |
| `reliability-dev` | `conda run -n reliability-dev python -I` | 신뢰도 해석(openturns). dynamics-dev와 한 프로세스로 섞지 않는다 |
| `python-dev` (Py 3.13) | `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I` | 에이전트 보조 도구(`~/.claude/tools/`의 cpu-scheduler·monitor·integrity·paper·pdf·docx·pyinspect), 논문 빌드(pandoc, latexmk용 Strawberry Perl). `MKL_THREADING_LAYER=TBB` 영구 설정. 프로젝트 시뮬레이션에는 쓰지 않는다 |

- 패키지를 더할 때는 conda에 있으면 conda를 먼저 쓴다.
- Chrono 9 이후로는 충돌 시스템을 지정해야 접촉이 생긴다: `sys.SetCollisionSystemType(chrono.ChCollisionSystem.Type_BULLET)`.
- 시각화는 `pychrono.irrlicht`를 쓴다(`pychrono.vsg3d`는 쓰지 않음). 대화형 VTK 조회는 ParaView 6.2.0 MPI판 + paraview MCP(cad-expert·dynamics-expert)로 한다.
- MuJoCo는 **인터페이스만** 둔다(`SimEngine` 프로토콜 유지, 백엔드 없음). 교차 검증은 Chrono와 독립인 numpy 모델로 한다.
- ML env의 numpy는 **MKL + TBB 스레딩 계층**이다. torch를 먼저 import하고 MKL 기본 계층이면 행렬곱에서 프로세스가 죽는다(0xC06D007F). `MKL_THREADING_LAYER=TBB`가 conda 환경 변수와 `sitecustomize.py`에 걸려 있다(env를 다시 만들면 `sitecustomize.py`도 다시 만든다). 학습 데이터는 Chrono-dev가 만든 npz를 읽고, 두 env를 한 프로세스로 섞지 않는다.
- 계산 비용 측정·장시간 실행은 **P코어 고정 + EcoQoS 해제**로 한다(i7-14700, P 8 + E 12; Windows가 창 없는 하위 프로세스를 E코어로 보내 느려진다). 구현 `04_scripts/02_chrono/solver_benchmark/step_cost_S0.py`의 `place_process`. 비용 측정은 다른 계산과 겹치지 않게 혼자 돌린다. 그 밖의 계산은 컴퓨터 자원을 최대한 쓴다(배치표·실행 명령은 compute-scheduler-expert, 스스로 코어를 고정하는 Chrono 사례는 `self_pin: pcore`로 동시 개수만 받는다).
- PARDISO_MKL은 env 미활성 실행에서 `Library\bin\libomp.dll`을 미리 로드해야 한다(`chrono/system.py`가 처리).

## 현재 기준값 (2026-10-30)

| 항목 | 값 | 원본·비고 |
|---|---|---|
| 상부체 질량 | **38,400.8 kg**(경우 C: 오거 공구만 강재, 나머지 STEP 밀도, REXOME35 배럴 −155 kg 반영) | YAML `superstructure`. 운용 중량 확인 전까지 유지. 운용 중량으로는 과소일 가능성이 크다 |
| 오거 3단계 | 상단 +2.996 m / 중단 −1.303 m / 하단 −5.602 m(CAD 대비 z 이동). **기본 실행은 상단**, 제어기 검증은 세 단계 모두 | `01_cad/03_auger/auger_levels.json`, `00_docs/00_cad/cad_auger_levels.md` |
| 실린더 | REXOME35 도면: 전방 ø130/ø110, 후방 ø110/ø90, 행정 700 mm | `08_test_data/datasheets/cylinder_{front,rear}_extract.md` |
| 행정 | 플랜트 0.70 m, 센서 끝 0.6948 m, FAULT 0.6938 m, 끝 여유 기준 0.6848 m. 수축 오프셋 계산(기하)에는 CAD 추정 680 mm를 그대로 쓴다 | YAML `actuator.stroke_m`, `legs.*.extension_range_m` |
| 속도·램프 | 최대 **20.924 mm/s**(네 다리 동시, 펌프 60.2 L/min × 0.95), 명령 램프 0→v_max **0.1 s** | YAML `actuator.max_speed_m_s`, `command_ramp_s` |
| 힘 한계(다리별) | 신장 210 bar: 전방 **278.7** / 후방 **199.6 kN**, 수축 210 bar: 79.2 / 66.0 kN, 잠김 350 bar: 464.6 / 332.6 kN | YAML `legs.<leg>.cylinder.*`. `actuator.max_force_*`(218/18.6 kN)는 폐기값 |
| 압력 판정 | 이동 중 최대 210 bar(릴리프, 행정 끝), 잠김 정지 ≤ 350 bar, 경고 345 bar | 포화 정지는 2 ms 감속, 판정은 F_cyl − m_rod·a |
| F_min | **9.415 kN**(다리당 평균 하중의 10 %, 실린더 순 힘 p_h·A_p − p_r·A_ann, 영점 교정 후). 제어기 문턱은 모두 "F_min + 여유" | YAML `control.F_min_cylinder_N` |
| 유압유 β_eff | **1.0 GPa**(감도 0.69~1.6) | YAML `actuator.oil_bulk_modulus_eff_Pa` |
| 사체적 | 로드측 L_0r 0.05 m(감도 0.02~0.1), 헤드측 L_0h 0.05~0.08 m | 제조사 블록 체적 확인 대기(Q-M12) |
| 실 마찰 | 공칭 F_s 4 kN(전방), 후방 = 전방 × 0.833, 감도 **0 / 2 / 4 / 8 kN**. L2b에만 넣는다 | `00_docs/02_hydraulic/s8_seal_friction_counterbalance.md` |
| 로크 밸브 | 파일럿 체크 기본, 카운터 밸런스는 옵션 `lock_valve="counterbalance"` | YAML `actuator.lock_valve` |
| 감쇠비 | 다리(잠김) 0.03, 이동 중 0.10, 크롤러 콘크리트 0.05 / 토양 0.2, 구조·마스트 0.015. 다리 감쇠계수는 LOCK 강성 heave 모드 기준(YAML 유도값 8.88 Hz; 옛 치수 때 약 7.4 Hz) | `00_docs/01_dynamics/damping_survey.md` |
| 시간 간격 | L1 **2×10⁻⁴ s**, L2b-NSC 1×10⁻⁴ s, 기준해·접지 전환 1×10⁻⁵ s, L2 5×10⁻⁵ s | YAML `simulation.*.dt_s` |
| 선형 솔버 | L1(SMC) SPARSE_LU + `LockSparsityPattern(True)`, L2b(NSC) PSOR 50회 | `06_analysis/01_chrono/01_cost/solver_benchmark.json` |
| 크롤러 접촉 | D안(롤러 위치 6개/측 + 끝 슈 3개/끝), 총 강성 1×10⁸ N/m(×3 감도). L2b는 **강체**(NSC 유연 접촉 안 1은 PyChrono 10에서 크리프로 동작해 불가) | YAML `contact.crawler` |
| 센서·주기 | 압력 헤드·로드 각 1개(WIKA A-10, 0~400 bar, ±4 bar; 실린더와 파일럿 체크 블록 사이 챔버 쪽 A·B 포트), 압력·행정 센서와 밸브 출력 **10 Hz 순간 표본**, IMU **100 Hz**. 압력 영점 교정은 CHECK 단계에서 의무(복귀 판정은 시간 초과 때 최소 변위 ≤ 0.5 mm면 인정, D안, 명세 416). 센서 오차는 3등급 모델(오프셋·스팬·비직선·비반복·노이즈). 압력 센서 오차는 **conservative 등급 이하**(온도 오차 영점 ±4 bar·스팬 ±0.5 % 이내; old_worst ±10 bar·±1 %는 불가, P-S8-29 완화 READY 지연 방지, 결정 Q-F 2026-10-29, 명세 423.2) | `c2.py` `R8_PERIOD_S`·IMU 표본 주기, `08_test_data/datasheets/WIKA_A-10_pressure_sensor_summary.md`, YAML `sensors.cylinder_pressure`(두 센서 순 힘, 2026-10-25 재생성) |
| 제어기 | **R8 C2**: 10 Hz, 출력 지연 d = 1, 주기 시작 IMU. 프리셋 `C2Config.with_10hz_d1()`(`03_src/outrigger_sim/control/c2.py`). 가드 이득 0.15, 비틀림·가드 이득 S_ii 정규화, R-5 예측 4주기, 증분 제한 대칭 0.25 v_max/주기, 재접근 시작 1.4 F_min, 재접근 재발동(직전 회차 끝 2.0 s 안) 속도 ×0.6·반대 대각(0.8 s 안)은 하한 < 0 N 2표본 연속일 때만 시작(아니면 보류). 토양 대응 기본 켬(U-S9-C1): 크롤러 이탈 확인(LOC, 10 mm 창 평탄 상승 ≤ 2 kN, U-S9-C2), 해제 전 LOC가 없으면 토양 모드, 모서리 보정은 ĉ_min(t_P) > 20 mm일 때만(U-S9-C7), 재접근 시간 한계 10 s → `WARN_LEG_REAPPROACH_NO_CONTACT`, 가드 경로(U-S9-C4). 헤드 압력 고장 때 뜬 다리만 재접지 뒤 FAULT(FAULT_REGROUND, U-S8-68·72), D1″ 적용 = LOC 확정 + 크롤러 재접촉 의심 보류, 첫 READY 전 D1″ 질량 = YAML 명목(U-S8-69·70), 헤드 고장 뒤 D1 계단 판정 정지. TOUCH 자유공기 기준 상한(P-S8-26, 다리별 m_rod·g + 8 / 6.67 kN)·TOUCH 래치 후보 골 2표본 허용(P-S8-27, `touch_hold_dip_samples` 2). 비평면 시작 대응(P-S8-28, U-S8-78·79): LOC 기준 크롤러 틈(c_min(t_P) < −20 mm면 행정 변화량 평면 맞춤, ĉ₀ −5 mm), 행정 예산 가드(682.8 mm에서 틈이 충분하면 네 다리를 같이 낮추고 아니면 네 다리 정지 → `WARN_LIFT_STROKE_LIMITED` + DONE, 3 s 넘으면 `FAULT_LIFT_STROKE_LIMIT`), `FAULT_STROKE_END`, 행정 끝 FAULT 때 뜬 다리 재접지(30 mm). 비틀림 완료 완화(P-S8-29 V2b): LOC 뒤 자세·틈 10 s 유지 + 5 s 창 |D| 비증가(재상승 허용 0.6 kN, U-S8-80) + |D| ≤ 15 kN + 네 다리 하한 ≥ F_min이면 DONE(`INFO_TWIST_UNSETTLED`). READY 꼬리 생략 여유 0.5 mm. LOC 전 느린 들어 올림(P-S8-30 P30fz): 토양 대응 LEVEL·LOC 전·토양 모드 전에 하한 < 3 F_min으로 표본당 ≥ 2 kN 떨어지는 다리가 있으면 평균 0.16 v_max로 ≤ 3 s(`INFO_LIFT_PAUSED`), LOC 전 재접근 ×4. 경사 틈 여유(P-S8-31 E3c10, 결정 11): LOC 때 정착 기울기 > 1°이고 c_min(t_P) > 10 mm면 틈 목표 +30 mm(`INFO_LOC_CLEARANCE_MARGIN`). LOC 창 재시작(P-S8-32 LWa, 결정 12): LOC 전 재접근 중에는 S-1 평탄 창을 비우고 다시 셈(`INFO_LOC_WINDOW_RESTART`). LOC 사후 취소(P-S8-33 L1gs, 결정 Q-D 2026-10-29, 명세 424.10.2): LOC 뒤 평균 행정이 20 mm 늘 때까지(또는 첫 DONE까지) 하중 합 1 s 평균이 Ŵ + max(2 kN, 0.005 W_ref)를 2주기 연속 넘으면 LOC 취소(최대 2회, `INFO_LOC_REVOKED`), 토양 징후(토양 모드 또는 c_min(t_P) > 10 mm·정착 기울기 > 1°)가 있는 LOC에서만 감시, 최대 행정 ≥ 642.8 mm면 취소 안 함(`INFO_LOC_REVOKE_SKIPPED:stroke`), E3c10은 첫 적용 유지. P-S8-34(확인창)는 폐기. LOC 뒤 차등 침하 보상(P-S8-35 DSb75, D424 ① 실패 뒤 밤사이 사전 결정으로 설계, 명세 424.11~424.11.2): 첫 LOC~첫 DONE, 토양 징후 + 정착 기울기 ≤ 1°일 때 축별 r = (ṡ_L − ṡ_R) − w·φ̇(자이로) > 3 mm/s가 1 s면 가라앉는 쪽 다리에만 Δu = min(1.5|r|, 0.75 v_max) 추가(반대쪽·자세 루프 그대로), 부호 반전·< 1 mm/s 0.5 s·10 s·행정 642.8 mm에서 해제, 작동 중 DONE 금지(`INFO_DIFF_SINK_*`), LOC 취소와 무관하게 첫 DONE까지 감시. 알려진 한계: 연구 ① `H1|S1|A|top|roll_neg`(roll 4.4°, R_c = 1.0) 행정 한계 FAULT(안전 종료), Chrono D424R 운용 중량 +10 % J1 패드 B 상단 READY 103.3 s(P3-6 한계 100 s 초과, 그 밖 판정 통과), 연약 경사에서 행정 가드 작동 뒤 크롤러 재하중 상태로 READY(명목 2/177, ×1.1 3/21) → P-S8-36 SGS 채택(가드 첫 주기 안전 정지 `FAULT_LIFT_STROKE_LIMIT:soil`, 판정 `stroke_limited_stop`; 무장 범위는 토양 대응 실행의 모든 LOC, 결정 2026-10-30, 명세 427.12). **최종 제어기(2026-10-30, 명세 429.9~429.11) = R8 C2 + L1gs + DSb75 + SGS any_loc + R4c30**(평지 토양 LOC 틈 목표 +30 mm, `flat_soil_margin_m`). P37t(비틀림 장부)·ZIC(P-S8-38 적분 제한)는 기각. R8 프리셋 `with_10hz_d1()` 기본값으로 켬(`soil_stop=True`, `flat_soil_margin_m=0.03` = `R8_FLAT_SOIL_MARGIN_M`, 2026-10-30 B1 통과 뒤 전환, 429.11; 클래스 기본값은 꺼짐, 전환 전 해시 재현은 `05_tests/unit/pre_switch_preset_runner.py`). 논문 Chrono는 대표 최소 7건(FINAL-REP, 명세 432), ×1.1 S1 대각 경사 LOC 밀기 예산 150 mm 소진 → FAULT(한계 기록, 명세 426.9.B1). 운용 중량 +20 %(J1 패드 B)는 범위 밖(A-2 개정). 판정: 재접근으로 늦어진 LOC의 P3-2·G6-2 위반과 U-S9-G6d 과도 재접촉은 FLAG(419.8) | `s6_control_spec.md`(개정 30~84, 토양 대응 285·293·295·297절, 고장 대응 320~340절, 수정 414~424절, 기준선 비교 425절). 게인·세부는 명세가 원본 |
| 자세 필터 | 2차 저역통과, R8 C2 **τ 0.8 s × 2단**(IMU 10 ms 표본, 100 Hz 계산). 자세 PI Kp 0.2 s⁻¹·Ki 0.01 s⁻², 비틀림 Ktw 0.5 s⁻¹ | `c2.py` `R8_D1_*` 상수, `s6_control_spec.md` 136절. 0.5 s × 2·Kp 0.4는 R7(50 Hz) 값. 1차 필터는 쓰지 않는다 |
| 정확도 | 정상상태 오차 **±0.2°**, 완료 데드밴드 0.03°, IMU 정지 영점 오차 허용 0.14°(장착 몫 0.02°). IMU 현장 영점 교정 의무. 연약 지면(S9 P3b)은 마지막 탐침 소성 침하로 끝 자세 0.03~0.07°가 남아 IMU 선정 조건(영점 오차 허용) **≤ 0.118°**(U-S9P-16) | `00_docs/05_sensors/imu_cabin_and_accuracy_review.md`, `s6_control_spec.md` 311절·432.4.6 |
| IMU 위치 | 기체 좌표 (0.31, 0.88, 0.040) m, 캐빈 아래 상부 프레임 C1(캐빈 몸체에 달지 않음, 낮게 단다) | `00_docs/00_cad/cad_origin_mass_imu.md` 4절 |
| 레벨링 시작 조건 | 운용: \|φ_g\|/4.4° + \|θ_g\|/3.2° ≤ 1(크롤러 위 IMU 자세). 시뮬레이션 검증 범위: 바닥 경사 5.5° / 3.5°. 넘으면 시작하지 않고 경고. 연약 지반·패드 B 운용 권고: 좌우 ≤ 2.64°(R_c 0.6), 앞내림·대각 R_c ≤ 0.875, 넘으면 목표 미달 안전 정지가 날 수 있음(roll 양 2.64° Chrono 확인 중) | `dynamics_model.md` 3.9.7절, `s6_control_spec.md` 430.3.3·430.3.4·432.4.7. 후방 로드 소재(C45) 확인 시 앞들림 재판정 |
| 목표 범위 | 축별 상한 pitch ±3°, roll ±4° + 마름모 검사(규칙 A), 밖이면 거부·경고 | `dynamics_model.md` 3.12절 |
| 고착점 재설정(H4) | 앞내림에서만, 목표 대비 상대 pitch ≥ 2.5°일 때 | `c2_design.md` 17절 |
| 접지 판정 | **압력 절대값만으로 접지·F_min을 판정하지 않는다**(U-S8-22 확정). 압력·스트로크·IMU 결합 판정 + 탐침(자세 변화 ±0.1° 안). ML/DL은 비교 후보 | `s6_control_spec.md` |

## 모델 규약

- 4점 지지는 부정정이다. 남은 다리는 하중 분배를 정하므로, 제어 목표에 "모든 다리 접지 유지"(반력 > 0, 실린더 힘 ≥ F_min)를 포함한다.
- **구동기 운용안 B**: 제어기 개발·대량 실행은 **L1**, 큰 경사·실 마찰·연약 지면 재판정은 **L2b**(L2 + 횡 부싱)로 병행한다.
  - L1(L1-R) = 강체 위치 모터(훅에서 s_ref 적분, 속도 모터 쓰지 않음) + 유압유·접촉 직렬 유연성을 합친 집중 접촉(상태 기계·예측자) + 로드측 챔버 한쪽 방향 비선형 병렬 스프링(잠긴 상태만, 바닥 0.1 bar abs). 감쇠는 LOCK 기준 단일 값.
  - L2b = `ChSystemNSC` 접촉 + `ChLinkMotorLinearForce` Python 힘 법칙(PyChrono 10은 C++ 유압 클래스를 노출하지 않음).
- Chrono 10 SMC 접촉에는 **정지 마찰이 없다**. 그래서 L1 패드는 지면 고정 `ChLoadBodyBodyBushingSpherical` + 매 스텝 원형 Coulomb 항복 처리(`SetApplicationFrameB`로 고정점 이동)를 쓴다. `ChLoadBodyBodyBushingPlastic`은 쓰지 않는다.
- Chrono 함정: Hooke `gn`·`gt`는 유효 질량당 값이라 고정 바닥 바디 질량을 크게(예: 1e9 kg) 둔다. 부싱 감쇠는 입력의 2배로 작용하므로 ct/2를 넣는다. `GetPos()`는 참조라 저장할 때 복사한다. 훅 입력은 다음 스텝부터 반영된다(1스텝 지연 규약).
- 패드는 팔각(정사각 + 모서리 모따기)이고 방향은 CAD 그대로이며, 로드와 **구면(스위블) 조인트**로 잇는다. 면적은 실험 변수다(U-PAD-1~6): 타입 B `dwg_rear250`(**기본**: 전방 330 0.1071 m², 후방 250 0.0607 m², 모따기 30 mm 가정) / 타입 A `cad330`(네 다리 0.1071 m²). 형상 원본은 YAML `pad_shapes`(기본 `default_type`), 대응표 `02_params/pad_variants.json`, 실행 인자 `--pad-variant`(`outrigger_sim.pad_variants`). L1·L2b 강체 지면은 면적을 쓰지 않아 결과가 같고, SCM(S9)에서만 차이가 난다. 후방 패드는 CAD보다 2 mm 올린 위치가 완전 수축(0 mm)이다.
- 스트로크 센서는 실린더 내장형으로 가정한다: `stroke_true = s_motor − F_cyl/k_oil`.
- 센서 모델은 `03_src/outrigger_sim/sensors/`에 둔다. IMU 영점 오차는 센서 등급 잔차만 쓴다(교정 절차는 모델링하지 않음).
- 실 마찰 F_s는 점성 감쇠에 섞지 않고 따로 모델링한다.
- 강체 모터 + 콘크리트 접촉만(R1)은 하중 평가에 쓰지 않는다(하중 민감도 약 15배 과대).
- 지면은 두 가지다: 강체(Chrono 접촉), 연약(S9, `SCMTerrain` Bekker-Wong). S9에서만 패드 hull(패드 바디 + 구면 조인트)과 트랙당 포락선 상자 3개를 접촉에 쓴다. C8 충돌 형상은 S1~S8에서 시각화·간섭 확인 전용이다.
- 들어 올림 하중은 동적 피크를 기록하고 다리별 힘 한계만 판정한다. 주행 시험 트랙(T, 선택)은 레벨링 모델과 분리한다(`00_docs/03_chrono/track_drive_plan.md`).

## 도메인 용어

| 용어 | 뜻 |
|---|---|
| 상부체 | 아우트리거 4개가 받치는 구조물. 자세 제어 대상인 강체 |
| 아우트리거 (leg) | 상부체를 지면에 지지하는 다리 4개. 신장 길이를 제어한다 |
| 레벨링 | 상부체 roll·pitch를 목표값(보통 0)으로 맞추는 동작 |
| 접지 / 부상 | 다리가 지면 반력을 받는 상태 / 반력이 0이 되어 뜬 상태 |

## 좌표계와 명명

다리 이름과 좌표계는 아래 정의를 따른다. 바꿀 때는 이 절을 먼저 고친다.

- 기체 좌표계: x 전방, y 좌측, z 상방 (오른손 좌표계). roll은 x축, pitch는 y축 회전이다. pitch θ > 0 = 앞내림.
- 전방은 마스트와 `FRONT JACK CYL`이 있는 쪽이다.
- CAD 축 대응: x = +Z_cad, y = +X_cad, z = +Y_cad (CAD는 Y-상방, 길이 mm). 회전행렬(기체 ← CAD) `[[0,0,1],[1,0,0],[0,1,0]]`.
- 다리 순서: `FL`(전방 좌), `FR`(전방 우), `RL`(후방 좌), `RR`(후방 우). 배열 인덱스는 이 순서로 0–3이다.
  - CAD 대응: FL = `FRONT JACK CYL:1`, FR = `FRONT JACK CYL:2`, RL = `REAR JACK CYL:1`, RR = `REAR JACK CYL:2`.
  - `cad_summary.json`의 패드 z 값은 패드 **바닥면** 높이다 (질량 중심 아님).
- 기체 좌표 원점: CAD 원점 = 선회 링 볼트원 PCD 1,120 mm 중심축 ∩ 데크 하면. 지면(크롤러 바닥) z = −1.0509 m.
- 단위는 SI(m, kg, s, rad)다. 각도는 표시할 때만 도(°)로 바꾼다.

## 미정 사항

이 목록이 현행이다. decision_log 12절은 2026-10-25 이관 때의 원문 스냅숏이다.

- 상부체 운용 중량(엔진·작동유·연료, 운전실·오거 공구·크롤러 실제 질량). 크롤러 하부체는 다른 기종(REXOME25) 모델이다.
- 연약 지면 SCM 파라미터: 문헌 기반 세트로 확정(U-SOIL-1~4, `02_params/scm_soil_sets.json`). 현장 값(평판재하)은 미확인이며 오면 교체한다. G1 다짐 자갈은 K30 대체 근거이고 지지력은 조건부다.
- 유압 사양(배관, 응답 시정수 τ_v), 접촉 강성·감쇠 실측값 — 지금은 가정치. 실 마찰은 단품 시험 3.72 kN을 근거로 공칭 4 kN(근거 있는 가정치). 카운터 밸런스 파라미터는 모두 가정(제조사 확인 U-S8-H5).
- 하드웨어 확인 U-R8-9: 압력 표본→출력 흔들림 ≤ 20 ms, IMU 전송 지연 ≤ 20 ms, τ_v 실측. ④에 로드측 해제 1 kHz 기록·신장 배압·밸브 중립 형식·B 호스 체적을 더한다(R-5). 2026-10-26 추가(H-61-1): 중립이 A·B 차단이면 잠금 뒤 PO 체크가 닫히는지(열린 채면 행정 ≤ 0.40 m에서 수준 상계 R_ub·R_hi가 상계가 아님), 피스톤 내부 누설 시험값(≤ 4 cm³/min @ 70 bar), CHECK 단계 전용 압력비 동정(하중 변화 ≥ 30 bar, 1 kHz). 실기 R_hi κ_hi 상태식 구현(P-S8-22b)은 이 확인 뒤. ④ 본문: 체크 밸브 실제 닫힘 시간(잠금 창 τ_v 의존). ⑤ 압력·IMU·자이로 타임스탬프 정렬 ≤ 5 ms(D1″ IMU 비력 잔차의 전제, 20 ms 어긋나면 거짓 헤드 고장; IMU 내부 디지털 필터 군지연·10 ms 부분 평균 제공 여부 포함), 같은 타격 시험으로 로킹 자유 감쇠·heave 진동수 기록(10 Hz 앨리어싱 판단). 잠김 로킹 감쇠 보강(2026-10-27 채택, `dynamics_model.md` 5.39.6): 크롤러 들어 올린 잠김 상태(상단·평지)에서 데크 측면 횡 충격 두 진폭(다리 축 ≥ 0.5 mm / ≤ 0.1 mm), IMU ≥ 100 Hz·압력 1 kHz·≥ 20 s, 진폭별 f·ζ 식별. 큰 진폭 ζ ≥ 0.009면 현행 모델 유지(모델 ζ 0.009는 보수 쪽 하한).
- U-S8-59(U-R8-9 ④ 뒤): 실기 로드측 배수 진단 규칙 — 두 주기 보류 또는 단조 하강 보류(δ 1 bar, 2 s). 시뮬레이션 플랜트는 한 주기 보류로 충분.
- S9 뒤 계속 감시(P3b에서 보류 0건이라 미관측): RT 보류 중 보류 다리 하중 저하(U-S8-57), DONE 관문의 느린 꼬리(READY 분포).
- 커버리지 공백(감사 2026-10-27): G3(앞 다리 사건 + 그 다리 로드 고장), G6(SCM 한 패드 연약부)는 하네스·P-S8-29·P-S8-30·Chrono SCM 확인까지 끝나고 센서 오차 모델 하네스 확인이 남음(개정 72~75; 하네스는 J1 연약 패치에서 낙관 쪽), 크롤러 재접촉 합성 사례(명세 322.2, 나중). R8 PS-7a·b·c(사전 접지 시작)는 개정 68, G5(중간 F_s)·G8(비평면 시작)은 개정 69~71에서 닫음.
- 접지 판정 ML 재개(선택, S9 이후): 높은 F_s·첫 탐침 전 표적 데이터, F_s,air 입력, 정정된 판정 규칙(U-S8-53·54).
- 제조사 확인: 후방 로드 소재(C45면 앞들림 한계 재판정), 전방 팔 핀·부싱(Q-L2), 평형추 결합(Q-L3), 센서 블록 체적(Q-M12), 마스트 붐·백스테이 실린더 잠김(Q-B3·Q-B1·Q-B4·Q-B2).
- 마스트 유연성: S1~S8은 강체 마스트, D2·V17 전에 방향별 1모드 유연 마스트를 넣는다.
- IMU 센서 모델 선정, 장착점 C1 실기 확인(점검구 접근, 판 국부 강성).
- 주행 시험(T): 주행 모터 사양, 트랙 장력, 스프로킷 맞물림, 상부 롤러 회전부 질량·관성.

## 작업 규칙

- Chrono 해석 결과(`06_analysis/01_chrono/`)는 하위 폴더로 나눈다: `00_conventions`(규약 시험), `01_cost`(솔버·스텝 비용), `11_S1`~`19_S9`(단계별 판정 `verify_S*_L1.json/.png`, 결과 그림, 렌더 메타 `*_gifs.json`; 바꾸기 전 결과 보관본은 그 단계의 `history/`), `20_track_drive`(주행 시험 T). 새 단계 산출물도 해당 번호 폴더에 쓴다.
- 시뮬레이션 공통 파라미터의 단일 출처는 `02_params/rexome33.yaml`이다. Chrono·MuJoCo 모델은 모두 이 파일을 읽는다. 생성물이므로 손으로 고치지 않고 `04_scripts/00_cad/export_params.py`로 다시 만든다. 블록마다 출처 주석이 있고 가정은 `ASSUMPTION`으로 표시돼 있다. 덮어쓰기 전 원본은 `02_params/history/`에 보관한다.
- CAD 원본(`*.stp`)은 약 630 MB라 git에서 제외한다. 읽을 때는 파일 전체를 열지 않는다. 헤더·단위·조립 트리·BOM·한글 이름은 cad-expert 도구 `~/.claude/tools/cad/step_inspect.py`(텍스트 스트리밍)로 먼저 보고, 그 밖의 엔티티는 `grep -a`로 뽑는다. 한글 부품명은 STEP `\X2\…\X0\`(UCS-2 hex)로 인코딩돼 있다.
- CAD 자동 추출(부품 표, 부피·무게중심·관성)은 `Chrono-dev`의 pythonocc-core로 한다(cad-expert 도구 `mass_props.py` 우선).
- FreeCAD 1.1.4(`C:\Program Files\FreeCAD 1.1\bin`)는 참고용 교차 검증(눈으로 확인, 치수 측정, 메시 내보내기 점검)에만 쓴다. 헤드리스는 `freecadcmd.exe script.py`(번들 Python 3.11은 Chrono-dev와 별개). FreeCAD를 Chrono-dev에 conda로 설치하지 않는다(OpenCASCADE 충돌). 630 MB STEP 전체 열기는 피하고 필요한 부품만 내보낸다.
- 결정이 생기면 [decision_log.md](00_docs/decision_log.md) 해당 절 끝에 한 줄로 더하고, 기준값이 바뀌었으면 위 "현재 기준값" 표를 고친다. 이 파일에 결정 경과나 재실행 판정 수치를 쓰지 않는다.

### 위임

- CAD 추출(부품 표·질량 특성)·형상 변환·Chrono 모델·시뮬레이션 스크립트는 cad-expert에, 그 밖의 Python 코드(제어기, IMU 모델, 데이터 처리, ML 학습) 작성·수정은 python-expert에 맡긴다.
- 동역학 해석(운동방정식·선형화, 4점 지지 하중 분배, 고유진동수, 적분기·시간 간격, 시뮬레이션 결과의 물리 타당성 판정, 플랜트 상태공간 모델)은 dynamics-expert에 맡긴다. Chrono 모델을 만들거나 바꿀 때는 `00_docs/01_dynamics/dynamics_model.md`의 검증 기준으로 판정한다.
- 제어기 설계·해석(C2·C8 구조와 게인, 루프 여유·지연, 안티와인드업, 강건성(오거 3단계·크롤러 강성·F_s), LQR·MPC·추정기 검토, 제어기 검증 항목 판정 기준)은 control-expert에 맡긴다. 주력은 고전제어다. 플랜트 모델은 dynamics-expert가 넘기고, 구현은 python-expert가 한다.
- 유압(L2 힘 법칙·β_eff, 잠긴 체적 압력 동역학, 밸브·파일럿 체크·카운터 밸런스·릴리프 모델, 실 마찰, 회로 해석, 유압 플랜트 선형화)은 hydraulics-expert에 맡긴다. 선형화 모델은 control-expert, 기계 쪽 판정은 dynamics-expert로 넘긴다.
- 논문 원고(`09_paper/`) 리뷰(심사위원 관점·프로젝트 근거 대조·도메인 기술·형식)는 프로젝트 에이전트 paper-reviewer(`.claude/agents/paper-reviewer.md`, 읽기 전용, 결과는 응답으로만)에 맡긴다. 논문 작성·교정·지적 반영·그림·표 규격화·LaTeX 빌드·서지(DOI) 확인은 전역 에이전트 paper-writing-expert에 맡기고 메인 세션이 원고를 직접 고치지 않는다(사용자 결정 2026-10-28). 지시문 첫머리에 `[모드] 작성|교정|빌드|서지|응답|진단`을 적고, 원본(`draft/*.md` 등)을 고치게 할 때는 원본 수정 허락을 지시문에 적는다(없으면 사본에만 고친다). 수치·해석의 도메인 판정은 도메인 에이전트, 그림 생성 코드의 수정은 python-expert로 넘긴다. 리포트의 `위임 필요`는 해당 전문 에이전트로 넘긴다. 호출할 때는 리뷰 종류에 따라 Agent 호출의 `model`·`effort`를 정의 파일의 '호출 모델·effort' 표대로 지정한다(사용자 결정 2026-10-28): 종합·투고 전·누락 점검·개정판 재점검 = opus/high, 절 하나·수치 대조 = opus/medium, 형식·편집·문장 = sonnet/medium, 짧은 확인 = sonnet/low.
