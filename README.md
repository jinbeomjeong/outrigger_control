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
| 성능 목표 | roll·pitch 목표값 대비 정상상태 오차 ±0.1° 이내 |
| 기체 제원 | 질량·무게중심·다리 부착 위치는 CAD 검토 후 확정 |
| 시나리오 | 마스트를 수직으로 세운 상태, 오거 위치 3단계(상단·중단·하단). 마스트를 눕힌 자세는 다루지 않음 |
| 참조 기체 | BUMA CE REXOME33 천공기 미니어처 (`REXOME33_Assy_r3(미니어쳐).stp`) |

## 폴더 구조

```
outrigger_control/
├── analysis/   해석 결과(작은 JSON). dynamics/ = 동역학 기준해
├── cad/        CAD 원본과 거기서 뽑은 치수·질량 자료 (STEP 원본은 git 제외)
├── docs/       설계 문서, 좌표계·모델 정의, 결정 기록
├── params/     시뮬레이션 공통 파라미터 (scripts/cad/export_params.py가 생성)
├── scripts/    실행·분석 스크립트 (cad/ = CAD 추출·파라미터 생성, Chrono-dev / dynamics/ = 동역학 기준해, dynamics-dev)
├── src/        Python 소스
└── tests/      테스트
```

## 동역학·구동기 자료

- [docs/dynamics_model.md](docs/dynamics_model.md): 모델 구조 권고, 기준해(하중 분배·민감도·고유진동수·전도 여유), 접촉·적분기 권고, Chrono 모델 검증 기준 V0~V13, 제어 구조 후보.
- [docs/hydraulic_fluid_survey.md](docs/hydraulic_fluid_survey.md): 유압유 체적 탄성계수 등 유압 특성 조사.
- 기준해 스크립트는 `scripts/dynamics/`(conda `dynamics-dev`, 프로젝트 루트에서 실행), 결과는 `analysis/dynamics/`.

## CAD 자료

- `REXOME33_Assy_r3(미니어쳐).stp`: Autodesk Inventor 2020에서 내보낸 STEP AP214 조립품(약 630 MB, 2023-05-10). 헤더 기재 외곽 치수는 11,556 × 7,036 × 3,114이고, 부품으로 잰 값은 11,488.5 × 7,034.2 × 3,073.1 mm(높이 × 길이 × 폭)다. 크기 때문에 git에서 제외한다.
- 길이 단위는 mm이고 실기 치수다. CAD는 Y가 위쪽이며, 기체 좌표와는 x = +Z_cad, y = +X_cad, z = +Y_cad로 대응한다(전방 = 마스트·FRONT JACK 쪽).
- 부품명에 "OUTRIGGER"는 없다. 아우트리거의 유압 실린더는 `FRONT JACK CYL` ×2(사용자 제공)와 `REAR JACK CYL` ×2다. `LOCKING CYL`은 오거용 실린더라 다리가 아니다.
- 상세 결과와 미확정 질문은 [docs/cad_review.md](docs/cad_review.md)(제원·다리)와 [docs/cad_mast_review.md](docs/cad_mast_review.md)(마스트 힌지·운송 자세, 참고용), [docs/cad_auger_levels.md](docs/cad_auger_levels.md)(오거 3단계 위치), 추출 스크립트는 `scripts/cad/`, 데이터는 `cad/`에 있다.
