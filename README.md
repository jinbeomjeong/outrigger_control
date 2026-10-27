# outrigger_control

아우트리거 4개로 상부체(아우트리거에 연결된 구조물)의 자세를 제어하는 시뮬레이션 프로젝트.

## 목적

- 4점 지지 상부체의 자세(roll·pitch)를 목표값(보통 수평)으로 맞추는 레벨링 제어기를 설계하고 시뮬레이션으로 검증한다.
- 4점 지지는 정역학적으로 부정정이므로, 자세와 함께 각 아우트리거의 접지·하중 분배도 관리한다(한 다리가 뜨는 상태를 피한다).

## 범위

| 항목 | 내용 |
|---|---|
| 대상 | 시뮬레이션만 (실물 하드웨어 없음) |
| 언어 | Python |
| 구동기 | 실물은 유압 실린더. 시뮬레이션에서는 필요에 맞게 단순화한 구동기 모델로 대체할 수 있다 |
| 자세 센서 | IMU |
| 물리 엔진 | Project Chrono (PyChrono) |
| 지면 | 강체(시멘트 바닥), 연약(단단한 토양, SCM 변형 지형) |
| 성능 목표 | roll·pitch 목표값 대비 정상상태 오차 ±0.2° 이내 (2026-10-20 ±0.1°에서 완화, IMU 현장 영점 교정 전제) |
| 기체 제원 | 질량·무게중심·다리 부착 위치는 CAD 검토 후 확정 |
| 시나리오 | 마스트를 수직으로 세운 상태, 오거 위치 3단계(상단·중단·하단). 마스트를 눕힌 자세는 다루지 않음 |
| 참조 기체 | BUMA CE REXOME33 천공기 미니어처 (`REXOME33_Assy_r3(미니어쳐).stp`) |

## 폴더 구조

```
outrigger_control/
├── 00_docs/        설계 문서, 좌표계·모델 정의, 결정 기록
│   ├── 00_roadmap.md       전체 로드맵·지금 위치·체크리스트(체크 원본은 계획 문서)
│   ├── decision_log.md     결정 이력·근거(U-*, Q-*, 재실행 판정)
│   ├── 00_performance_checklist.md  성능 목표 대비 점검표
│   ├── 00_cad/         CAD 검토(제원·다리, 오거 3단계, 마스트 참고용, 크롤러 접지 C7, 시뮬레이션 형상 C8, STEP 색 C11, 실린더 도면 대조)
│   ├── 01_dynamics/    동역학 모델·검증 기준 V0~V17(`dynamics_model.md`), 구동기 L2 검토, 감쇠 조사
│   ├── 02_hydraulic/   유압 회로 해석, 유압유 조사, L2 유압 모델 명세, 로드측 압력, S8 실 마찰·카운터 밸런스, 단품 시험 분석 (회로도 이미지는 git 제외)
│   ├── 03_chrono/      Chrono 구축 계획(`chrono_build_plan.md`)·검토, 정지 마찰 시험, 주행 시험 계획
│   ├── 04_control/     레벨링 제어 조사, 제어 구조 후보 비교, C2 설계(`c2_design.md`), 제어기 명세·판정(`s6_control_spec.md`, 현행 R8 C2)
│   ├── 05_sensors/     자세 센서 조사, IMU 장착·정확도 검토
│   └── history/        바꾸기 전 문서 보관본
├── 01_cad/         CAD에서 뽑은 치수·질량·그림 (STEP 원본은 루트에 두고 git 제외)
│   ├── 00_step/        STEP 헤더·제품 목록
│   ├── 01_parts/       부품 표·분류, 요약, 3면도
│   ├── 02_legs/        다리 형상(brep)·면 정보
│   ├── 03_auger/       오거 3단계 값·그림·하강 GIF
│   ├── 04_mast/        마스트 힌지 검토(참고용, 대용량 캐시는 git 제외), 마스트 보 단면 특성(C9)
│   ├── 05_meshes/      렌더용 메시 캐시 (git 제외)
│   ├── 06_brep/        전체 부품 B-rep 캐시(프로토타입 .bbrep는 git 제외)·배치 표·크롤러 파생 캐시, 목록은 01_cad/cache_manifest.json
│   ├── 07_faces/       전체 면 색인(C5): 면 종류·면적·중심·법선·축·bbox, CAD/기체 좌표, 상부 롤러 면 표 (csv.gz는 git 제외)
│   ├── 08_style/       STEP 색(C11): 인스턴스·프로토타입·면 색 표, 질의 04_scripts/00_cad/style_index.py
│   └── 09_sim_shapes/  Chrono 시각화 메시·충돌 후보(C8, 상부 롤러 포함; *_lowres.obj는 git 제외)
├── 02_params/      시뮬레이션 공통 파라미터 (04_scripts/00_cad/export_params.py가 생성)
├── 03_src/outrigger_sim/  시뮬레이션 패키지 (엔진 독립 코어 + chrono/, sensors/, control/(C2·R8, 압력 진단 two_pressure), hydraulics/(L2b 로드측·실 마찰·CB), ml/(접지 판정 ML 비교), scenarios/, verify/(단계별 판정기))
├── 04_scripts/     실행·분석 스크립트
│   ├── 00_cad/         CAD 추출·파라미터 생성·그림 (Chrono-dev)
│   ├── 01_dynamics/    동역학 기준해·판정 (dynamics-dev)
│   ├── 02_chrono/      Chrono 시험·단계 실행기 `run_S1.py`~`run_S8C.py`, `run_S8V15.py`, `run_S9.py`·`s9_batch.py`·`s9_batch_summary.py` (Chrono-dev)
│   ├── 03_control/     제어 해석·판정 보조 (dynamics-dev)
│   ├── 04_hydraulic/   유압 해석 (hydraulics-dev, Hopsan)
│   └── 05_ml/          ML 데이터셋·학습·보고 (`pytorch_214_cuda_python_313`)
├── 05_tests/       pytest (unit/, chrono/, verify/, data/)
├── 06_analysis/    해석 결과(작은 JSON·그림)
│   ├── 00_dynamics/    동역학 기준해, 제어 비교, IMU 검토
│   ├── 01_chrono/      Chrono 시험 결과: 00_conventions(규약 시험) · 01_cost(솔버·스텝 비용) · 11_S1~19_S9(단계별 판정 `verify_S*`·그림·렌더 메타, 보관본은 `history/`) · 20_track_drive(주행 시험 T)
│   ├── 02_control/     제어 해석 결과(R8 10 Hz, S8 판정 보조·ML 보고서)
│   └── 03_hydraulic/   유압 해석 결과
├── 07_results/     시뮬레이션 원자료 (git 제외; 단계 판정 요약은 06_analysis/01_chrono/1N_SN/에 복사)
├── 08_test_data/   단품 시험 자료·데이터시트 요약(실린더 도면, 압력 센서)
└── environment*.yml  conda 환경 정의(Chrono-dev, ML, dynamics-dev)
```

대량 배치 실행기(`run_S6C.py`, `run_S7.py`, `run_S7C.py`, `run_S8C.py`, `run_S8V15.py`, `run_S9.py level`)는 `--approved`가 있어야 실제로 돈다(없으면 계획·dry-run). 사용법은 각 스크립트 docstring을 본다.

전체 작업 순서·지금 위치·결정 마감은 [00_docs/00_roadmap.md](00_docs/00_roadmap.md), 패키지 구조와 단계별 구축 계획은 [00_docs/03_chrono/chrono_build_plan.md](00_docs/03_chrono/chrono_build_plan.md)를 본다.

## 테스트

`pyproject.toml`에 pytest 설정이 있다(`pythonpath = 03_src`, 마커 `chrono`/`sim`/`slow`). Chrono-dev 환경에서 프로젝트 루트에서 실행한다.

```
C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -m pytest -m "not slow"   # 일상 회귀
C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -m pytest 05_tests/unit      # 단위 시험만
C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -m pytest -m chrono       # Chrono 규약 점검만
```

## 생성물 (git 제외, 다시 만들기)

GIF 애니메이션과 큰 메시(`*.gif`, `*_lowres.obj`)는 git에 올리지 않는다(2026-10-20 결정: 다시 만들 때마다 이력이 커지기 때문). 저장소를 받은 뒤 필요하면 아래 명령으로 만든다. 프로젝트 루트에서 실행한다. `PY` = `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe`.

| 파일 | 명령 |
|---|---|
| `01_cad/03_auger/auger_levels/auger_descent.gif` | `PY -I 04_scripts/00_cad/render_auger_descent.py` |
| `01_cad/02_legs/leg_extension.gif` | `PY -I 04_scripts/00_cad/render_leg_extension.py` |
| `01_cad/04_mast/mast_steps/fold_side.gif`(참고용) | `PY -I 04_scripts/00_cad/analyze_mast.py` |
| `06_analysis/00_dynamics/leg_extension_loads.gif` | `C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I 04_scripts/01_dynamics/run_leg_extension_loads.py` |
| `06_analysis/01_chrono/01_cost/solver_benchmark_{L1,SCM,scale}.gif` | `PY -I -u 04_scripts/02_chrono/solver_benchmark/make_gifs.py all` (저장된 측정 결과 `07_results/solver_benchmark/`로 GIF만, 약 5분). 측정부터 다시: `PY -I -u 04_scripts/02_chrono/solver_benchmark/run_benchmark.py all --report` (약 50분) |
| `01_cad/06_brep/derived/crawler/crawler_lowres.obj` | `PY -I 04_scripts/00_cad/derive_crawler_cache.py` 뒤 `PY -I 04_scripts/00_cad/check_cache.py --write --cache 06_brep` (약 8분, 파생 파일 전부 다시 씀, `00_docs/00_cad/cad_review.md` 8.6절) |
| `01_cad/07_faces/*.csv.gz`(면 색인, 6.1 MB; 상부 롤러 면 표는 아래 행) | `PY -I 04_scripts/00_cad/build_face_index.py`(약 4분, 검증 포함) 뒤 `PY -I 04_scripts/00_cad/check_cache.py --write --cache 07_faces` |
| `01_cad/06_brep/derived/crawler/parts/*.bbrep`(크롤러 D안 접촉 부품 44개, 84.6 MB) | `PY -I 04_scripts/00_cad/derive_crawler_parts.py`(약 2분) 뒤 `check_cache.py --write --cache 06_brep` |
| `01_cad/06_brep/derived/crawler/parts/upper_roller_{L,R}1.bbrep`, `01_cad/07_faces/crawler_upper_roller_faces.csv.gz`(상부 롤러 2개) | `PY -I -X utf8 04_scripts/00_cad/derive_crawler_upper_rollers.py`(약 14 s) 뒤 `check_cache.py --write --cache 06_brep 07_faces` |
| `01_cad/09_sim_shapes/visual/*_lowres.obj`(C8 시각 메시 63 MB, `crawler_no_upper_rollers_lowres.obj` 포함) | `PY -I 04_scripts/00_cad/build_sim_shapes.py`(약 12분, E코어; 상부 롤러만 `--stage upper_rollers index --cpu pcore` 4 s) 뒤 `check_cache.py --write --cache 09_sim_shapes` |
| `06_analysis/01_chrono/14_S4/S4_modes.gif`, `S4_energy_v8b.gif`(S4 결과; `S4_summary.png`은 git 포함) | `PY -I -u 04_scripts/02_chrono/render_S4_gifs.py --jobs 4 [--only modes energy summary] [--mesh-cache <폴더>]`(저장된 S4 기록에서만, 모드 약 3분·에너지 약 2분) |
| `01_cad/cad_tracks_turntable.gif`(C7·C8·C11 종합; `cad_tracks_2026-10-21.png`은 git 포함) | `PY -I 04_scripts/00_cad/render_cad_tracks_summary.py [--only summary turntable] [--mesh-cache <폴더>]`(약 2분) |
| `06_analysis/01_chrono/11_S1/S1_settle_levels.gif`, `06_analysis/01_chrono/11_S1/S1_cross_top.gif`(S1 정착·무초기화 낙하 결과) | `PY -I -u 04_scripts/02_chrono/render_S1_gifs.py` (저장된 S1 Record에서 GIF만, 시뮬레이션 재실행 없음, 약 3분; `S1_auger_levels.png`·`S1_cross_top_frame.png`·`S1_gifs.json`도 다시 씀). Record가 없으면 먼저 `PY -I -u 04_scripts/02_chrono/run_S1.py all`(약 2.5분) |
| `06_analysis/01_chrono/12_S2/S2a_v7_free_vibration.gif`, `S2a_v12_slope.gif`, `S2b_v11_stroke.gif`, `S2b_crawler_settle.gif`, `S2b_contact_events.gif`(S2a·S2b 결과; 대표 PNG `S2a_summary.png`·`S2b_summary.png` 등은 git 포함) | `PY -I -u 04_scripts/02_chrono/render_S2_gifs.py --before-dir 06_analysis/01_chrono/12_S2/history/before_planA` (저장된 S2a·S2b Record·result.json·verify JSON에서만, 시뮬레이션 재실행 없음, E코어 4프로세스 약 10분 + 처음 메시 캐시 약 2분; `--mesh-cache <폴더>`로 재사용; 부분만 `--only v7 dt v12 v12png v11 ramp crawler events summary`; PNG와 `S2_gifs.json`도 다시 씀). `before_planA/`는 부싱 작용점 안 A 전(접촉점) 실행 결과 보관본. Record가 없으면 먼저 `run_S2a.py all`, `run_S2b.py all` |
| `06_analysis/01_chrono/13_S3/S3_lift_v4.gif`(S3 V4 들어 올림; 대표 PNG `S3_lift_v4_frame.png`·`S3_summary.png`·`S3_v5_v6.png`·`S3_v8a_energy.png`·`S3_v9_convergence.png`은 git 포함) | `PY -I -u 04_scripts/02_chrono/render_S3_gifs.py [--mesh-cache <폴더>] [--before 06_analysis/01_chrono/13_S3/history/before_yaml_dt2e-4/verify_S3_L1.json]` (저장된 S3 result.json·Record `v4_D_wdefault`에서만, 시뮬레이션 재실행 없음, 약 1.5분 + 처음 메시 캐시 약 2분; 부분 `--only lift v5v6 v8a v9 summary`; `S3_gifs.json`도 다시 씀). Record가 없으면 먼저 `run_S3.py run --only v4_D_wdefault`(약 1.5분). `before_yaml_dt2e-4/`는 YAML Δt 2×10⁻⁴ s 반영 전 S3 판정 요약 보관본(`S3_summary.png`의 전·후 비교 입력) |
| `06_analysis/01_chrono/20_track_drive/track_drive_smoke.gif`(궤도차량 API 연기 시험, 우리 크롤러 모델 아님) | `PY -I -u 04_scripts/02_chrono/track_drive/smoke_drive_gif.py` (약 1분) |

STEP 원본·B-rep·메시 캐시처럼 더 큰 생성물은 `01_cad/cache_manifest.json`과 `04_scripts/00_cad/check_cache.py`로 관리한다.

## 동역학·구동기 자료

- [00_docs/01_dynamics/dynamics_model.md](00_docs/01_dynamics/dynamics_model.md): 모델 구조 권고, 기준해(하중 분배·민감도·고유진동수·전도 여유), 접촉·적분기 권고, Chrono 모델 검증 기준 V0~V17, 제어 구조 후보.
- [00_docs/02_hydraulic/hydraulic_fluid_survey.md](00_docs/02_hydraulic/hydraulic_fluid_survey.md): 유압유 체적 탄성계수 등 유압 특성 조사.
- [00_docs/02_hydraulic/s8_seal_friction_counterbalance.md](00_docs/02_hydraulic/s8_seal_friction_counterbalance.md): S8 실 마찰·카운터 밸런스·로드측 배수(H-S8-5).
- [00_docs/04_control/s6_control_spec.md](00_docs/04_control/s6_control_spec.md): 제어기 명세·판정 원본(현행 R8 C2, 개정 66까지).
- 기준해 스크립트는 `04_scripts/01_dynamics/`(conda `dynamics-dev`, 프로젝트 루트에서 실행), 결과는 `06_analysis/00_dynamics/`.

## CAD 자료

- `REXOME33_Assy_r3(미니어쳐).stp`: Autodesk Inventor 2020에서 내보낸 STEP AP214 조립품(약 630 MB, 2023-05-10). 헤더 기재 외곽 치수는 11,556 × 7,036 × 3,114이고, 부품으로 잰 값은 11,488.5 × 7,034.2 × 3,073.1 mm(높이 × 길이 × 폭)다. 크기 때문에 git에서 제외한다.
- 길이 단위는 mm이고 실기 치수다. CAD는 Y가 위쪽이며, 기체 좌표와는 x = +Z_cad, y = +X_cad, z = +Y_cad로 대응한다(전방 = 마스트·FRONT JACK 쪽).
- 부품명에 "OUTRIGGER"는 없다. 아우트리거의 유압 실린더는 `FRONT JACK CYL` ×2(사용자 제공)와 `REAR JACK CYL` ×2다. `LOCKING CYL`은 오거용 실린더라 다리가 아니다.
- 상세 결과와 미확정 질문은 [00_docs/00_cad/cad_review.md](00_docs/00_cad/cad_review.md)(제원·다리)와 [00_docs/00_cad/cad_mast_review.md](00_docs/00_cad/cad_mast_review.md)(마스트 힌지·운송 자세, 참고용), [00_docs/00_cad/cad_auger_levels.md](00_docs/00_cad/cad_auger_levels.md)(오거 3단계 위치), [00_docs/00_cad/cad_mast_beam.md](00_docs/00_cad/cad_mast_beam.md)(마스트 보 단면·1차 굽힘 추정, C9), 추출 스크립트는 `04_scripts/00_cad/`, 데이터는 `01_cad/`에 있다.
