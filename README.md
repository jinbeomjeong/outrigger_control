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
│   ├── 00_cad/         CAD 검토(제원·다리, 오거 3단계, 마스트 참고용)
│   ├── 01_dynamics/    동역학 모델·검증 기준, 구동기 L2 검토
│   ├── 02_hydraulic/   유압 회로 해석, 유압유 조사 (회로도 이미지는 git 제외)
│   ├── 03_chrono/      Chrono 구축 계획·검토, 정지 마찰 시험
│   ├── 04_control/     레벨링 제어 조사, 제어 구조 후보 비교
│   └── 05_sensors/     자세 센서 조사, IMU 장착·정확도 검토
├── 01_cad/         CAD에서 뽑은 치수·질량·그림 (STEP 원본은 루트에 두고 git 제외)
│   ├── 00_step/        STEP 헤더·제품 목록
│   ├── 01_parts/       부품 표·분류, 요약, 3면도
│   ├── 02_legs/        다리 형상(brep)·면 정보
│   ├── 03_auger/       오거 3단계 값·그림·하강 GIF
│   ├── 04_mast/        마스트 힌지 검토(참고용, 대용량 캐시는 git 제외), 마스트 보 단면 특성(C9)
│   ├── 05_meshes/      렌더용 메시 캐시 (git 제외)
│   ├── 06_brep/        전체 부품 B-rep 캐시(프로토타입 .bbrep는 git 제외)·배치 표·크롤러 파생 캐시, 목록은 01_cad/cache_manifest.json
│   └── 07_faces/       전체 면 색인(C5): 면 종류·면적·중심·법선·축·bbox, CAD/기체 좌표 (csv.gz는 git 제외)
├── 02_params/      시뮬레이션 공통 파라미터 (04_scripts/00_cad/export_params.py가 생성)
├── 03_src/outrigger_sim/  시뮬레이션 패키지 (엔진 독립 코어 + chrono/, sensors/, control/, scenarios/, verify/)
├── 04_scripts/     실행·분석 스크립트
│   ├── 00_cad/         CAD 추출·파라미터 생성·그림 (Chrono-dev)
│   ├── 01_dynamics/    동역학 기준해 (dynamics-dev)
│   └── 02_chrono/      Chrono 시험 (Chrono-dev)
├── 05_tests/       pytest (unit/, chrono/, verify/)
├── 06_analysis/    해석 결과(작은 JSON·그림)
│   ├── 00_dynamics/    동역학 기준해, 제어 비교, IMU 검토
│   └── 01_chrono/      Chrono 시험 결과
└── 07_results/     시뮬레이션 원자료 (git 제외)
```

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
| `06_analysis/01_chrono/solver_benchmark_{L1,SCM,scale}.gif` | `PY -I -u 04_scripts/02_chrono/solver_benchmark/make_gifs.py all` (저장된 측정 결과 `07_results/solver_benchmark/`로 GIF만, 약 5분). 측정부터 다시: `PY -I -u 04_scripts/02_chrono/solver_benchmark/run_benchmark.py all --report` (약 50분) |
| `01_cad/06_brep/derived/crawler/crawler_lowres.obj` | `PY -I 04_scripts/00_cad/derive_crawler_cache.py` 뒤 `PY -I 04_scripts/00_cad/check_cache.py --write --cache 06_brep` (약 8분, 파생 파일 전부 다시 씀, `00_docs/00_cad/cad_review.md` 8.6절) |
| `01_cad/07_faces/*.csv.gz`(면 색인, 6.1 MB) | `PY -I 04_scripts/00_cad/build_face_index.py`(약 4분, 검증 포함) 뒤 `PY -I 04_scripts/00_cad/check_cache.py --write --cache 07_faces` |
| `01_cad/06_brep/derived/crawler/parts/*.bbrep`(크롤러 D안 접촉 부품 44개, 84.6 MB) | `PY -I 04_scripts/00_cad/derive_crawler_parts.py`(약 2분) 뒤 `check_cache.py --write --cache 06_brep` |
| `06_analysis/01_chrono/track_drive_smoke.gif`(궤도차량 API 연기 시험, 우리 크롤러 모델 아님) | `PY -I -u 04_scripts/02_chrono/track_drive/smoke_drive_gif.py` (약 1분) |

STEP 원본·B-rep·메시 캐시처럼 더 큰 생성물은 `01_cad/cache_manifest.json`과 `04_scripts/00_cad/check_cache.py`로 관리한다.

## 동역학·구동기 자료

- [00_docs/01_dynamics/dynamics_model.md](00_docs/01_dynamics/dynamics_model.md): 모델 구조 권고, 기준해(하중 분배·민감도·고유진동수·전도 여유), 접촉·적분기 권고, Chrono 모델 검증 기준 V0~V13, 제어 구조 후보.
- [00_docs/02_hydraulic/hydraulic_fluid_survey.md](00_docs/02_hydraulic/hydraulic_fluid_survey.md): 유압유 체적 탄성계수 등 유압 특성 조사.
- 기준해 스크립트는 `04_scripts/01_dynamics/`(conda `dynamics-dev`, 프로젝트 루트에서 실행), 결과는 `06_analysis/00_dynamics/`.

## CAD 자료

- `REXOME33_Assy_r3(미니어쳐).stp`: Autodesk Inventor 2020에서 내보낸 STEP AP214 조립품(약 630 MB, 2023-05-10). 헤더 기재 외곽 치수는 11,556 × 7,036 × 3,114이고, 부품으로 잰 값은 11,488.5 × 7,034.2 × 3,073.1 mm(높이 × 길이 × 폭)다. 크기 때문에 git에서 제외한다.
- 길이 단위는 mm이고 실기 치수다. CAD는 Y가 위쪽이며, 기체 좌표와는 x = +Z_cad, y = +X_cad, z = +Y_cad로 대응한다(전방 = 마스트·FRONT JACK 쪽).
- 부품명에 "OUTRIGGER"는 없다. 아우트리거의 유압 실린더는 `FRONT JACK CYL` ×2(사용자 제공)와 `REAR JACK CYL` ×2다. `LOCKING CYL`은 오거용 실린더라 다리가 아니다.
- 상세 결과와 미확정 질문은 [00_docs/00_cad/cad_review.md](00_docs/00_cad/cad_review.md)(제원·다리)와 [00_docs/00_cad/cad_mast_review.md](00_docs/00_cad/cad_mast_review.md)(마스트 힌지·운송 자세, 참고용), [00_docs/00_cad/cad_auger_levels.md](00_docs/00_cad/cad_auger_levels.md)(오거 3단계 위치), [00_docs/00_cad/cad_mast_beam.md](00_docs/00_cad/cad_mast_beam.md)(마스트 보 단면·1차 굽힘 추정, C9), 추출 스크립트는 `04_scripts/00_cad/`, 데이터는 `01_cad/`에 있다.
