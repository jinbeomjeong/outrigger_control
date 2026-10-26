# YAML 재생성 묶음 명세 (2026-10-25, S9 착수 전 작업 1)

작성: cad-expert. 상태: **완료(2026-10-26).** 명세 확정(D1~D11 결정됨, 2026-10-25 사용자 — D8은 R0~R3, decision_log 2절 끝) → 1~6단계(소비 코드·생성기 반영·재생성, 커밋 8616be9) → 회귀 R0~R3 끝, **묶음 탓 차이 0**(7절 끝 결과, 동등성 기록 `06_analysis/01_chrono/00_conventions/params_bundle_2026-10-25_equivalence.json`) → 8단계 문서 갱신. 아래 본문(0~7절)은 스테이징 당시 서술이고, 실제 값과 다른 곳에는 2026-10-26 주를 달았다.

- 스테이징 생성기: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\85e4a02e-5208-42d0-8012-d36d25080593\scratchpad\cad-run\yaml_regen\export_params_staged.py`(SHA-256 `3fdb62e6…`). 원본 대비 diff: 같은 폴더 `export_params_staged.diff`(±254줄, 18 hunk). **반영본(2026-10-26 확인)**: `04_scripts/00_cad/export_params.py`(SHA-256 `3cf17ab6…`, 커밋 8616be9). 반영 전 원본은 `02_params/history/export_params_2026-10-25_before_bundle.py`(`8d8e3f76…`).
- 스테이징 YAML: 같은 폴더 `staged_out\rexome33.yaml`(853줄, SHA-256 `ef2880f9…`), 점검표 `staged_out\rexome33_checks.json`(`passed: true`, 실패 0). **재생성된 프로젝트 YAML `02_params/rexome33.yaml`도 SHA-256 `ef2880f9…`(전체 `ef2880f98aa6a20d…87ce`)로 스테이징과 같다**(2026-10-26 확인). 옛 YAML은 `02_params/history/rexome33_2026-10-25_before_bundle.yaml`(`a7128d75…`).
- 실행: `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I run_generator.py <생성기> <출력 폴더> [--cylinders cad]`(같은 폴더). 실행기는 생성기 사본에 `--out-dir`를 주고, 프로젝트 YAML·checks·`export_params.py`·`pad_variants.json`의 SHA-256을 실행 전후로 비교한다(모든 실행에서 "변경 없음").
- 좌표·단위: 기체 좌표(x 전방, y 좌, z 상, 원점 CAD 원점), SI. CAD는 mm, Y-상방.

## 0. 요약

| # | 항목 | 결정안(권고) | 지문 영향 |
|---|---|---|---|
| 1 | `sensors.cylinder_pressure.location` | R6-P 현행 문구로 교체(다리마다 헤드·로드 WIKA A-10, 챔버 쪽 A/B 포트, 순 힘 $F=p_hA_p-p_rA_{ann}$) | 값 변경 → L1·L2b 모두 바뀜 |
| 2 | 표본 주기 | **YAML에 넣지 않는다.** `c2.py`(`R8_PERIOD_S` 0.1 s, `R8_IMU_SAMPLE_PERIOD_S` 0.01 s)가 원본. YAML `sensors` 블록 주석이 그 위치를 가리킨다. 사본 상수 일치 시험만 더한다 | 없음 |
| 3 | 폐기 공통 실린더 키 6개 | **삭제**(rexome35 모드). cad 회귀 모드에만 남긴다 | 삭제 → 바뀜 |
| 4 | `actuator.rod_side_chamber_model` | **삭제**(`actuator.rod_side`로 대체 완료) | 삭제 → 바뀜 |
| 5 | 패드 다각형·면적 | `legs.<leg>.pad`에서 빼고 SCM 전용 최상위 블록 `pad_shapes`(A `cad330` / B `dwg_rear250`, 기본 B)로 옮긴다. `params.py`에 `SCM_ONLY_HASH_PATHS = (("pad_shapes",),)` | 이동 시 1회 바뀜, 이후 타입 전환은 L1·L2b 지문 불변(실측 확인) |
| 6 | 낡은 서술 | `control.F_min_basis`(순 힘 기준), `meta.dynamics_stages.common/SCM`, `meta.frame.origin`(원점 확정), `meta.mass_basis.description`(배럴 교체) 값 갱신. 주석 7곳 갱신 | 값 변경분은 위와 같은 1회 |

- 물리 값(수치 잎)은 하나도 바뀌지 않는다. 트리 비교 결과 차이 23건은 모두 위 표의 삭제·텍스트 변경·추가다(4절).
- 따라서 **강체 지면 L1·L2b 거동은 비트 동일이 기대된다.** 회귀는 판정 재실행이 아니라 "지문만 바뀌고 결과는 같다"를 보이는 일이다(7절).

## 1. 항목별 변경 (옛 값 → 새 값)

### 1.1 압력 센서 위치 (항목 1)

| 키 | 옛 값 | 새 값 |
|---|---|---|
| `sensors.cylinder_pressure.location` | `"lock valve block on the cylinder (head chamber); reads the trapped load pressure while locked; p = F_cyl / head area"` | `"two sensors per leg, head and rod chamber, at the chamber-side A / B ports between the cylinder and the pilot-operated check block; read the trapped pressures while locked; net cylinder force F_cyl = p_h A_p - p_r A_ann with the per-leg areas legs.<leg>.cylinder.head_area_m2 / annulus_area_m2, zero-offset calibrated"` |
| 같은 키 주석 | "manufacturer description; head-side reading, rod-side pressure 0 assumed"(현 YAML) | R6-P / U52, WIKA A-10 0~400 bar ±4 bar(`08_test_data/datasheets/WIKA_A-10_pressure_sensor_summary.md`), 오차 모델은 `03_src/outrigger_sim/sensors`에 있음, 2026-10-25 전 값은 헤드만 문구였음 |

- 근거: CLAUDE.md 기준값 표 '센서·주기', 생성기 357행 주석(현재판), 2331~2339행 주석.
- 센서 등급·노이즈 수치는 YAML에 넣지 않는다(코드 3등급 모델이 원본, 이중 출처 방지).

### 1.2 표본 주기 (항목 2) — 단일 출처 결정안

| 안 | 내용 | 영향 |
|---|---|---|
| (가) YAML로 옮김 | `sensors.sample_period_s.{pressure, stroke, valve_output, imu}` 추가, `c2.py`가 YAML을 읽음 | 플랜트 지문에 제어 주기가 들어간다. R7(50 Hz)·R8(10 Hz) 같은 **제어기 변형을 바꿀 때마다 L1·L2b 스냅숏이 무효화**된다(스냅숏은 플랜트 상태만 담는데도). `c2.C2Config`(`c2.py:1051-1221`)와 `run_S6C.py:171`, `two_pressure.py:164`, `04_scripts/03_control/c2_cycle_timing.py:80`을 모두 바꿔야 한다 |
| **(나) c2.py 원본 유지(권고)** | YAML에는 수치를 넣지 않고 `sensors` 블록 주석에 위치만 적는다(스테이징 YAML에 반영됨) | 지문 영향 없음. 사본 상수 4곳이 어긋날 위험만 남는다 → 시험 1개로 막는다 |

- 권고 근거: YAML은 차량·플랜트 파라미터의 단일 출처다. 표본 주기는 제어기 설정(명세 `s6_control_spec.md`가 원본)이고, 같은 플랜트 스냅숏 위에서 바꿔 비교하는 실험 변수다.
- python 위임(P-7): `05_tests/unit/`에 `c2.R8_PERIOD_S == c2_cycle_timing.R8_PERIOD_S`, `c2.R8_IMU_SAMPLE_PERIOD_S == run_S6C.IMU_SAMPLE_PERIOD_S == two_pressure.IMU_GYRO_SAMPLE_PERIOD_S` 시험(04_scripts 모듈은 import 경로 주의, 값만 비교).

### 1.3 폐기 공통 실린더 키 (항목 3·4)

| 키(현 YAML 행) | 현 값 | 대체 키 |
|---|---|---|
| `actuator.bore_diameter_m`(156) | 0.115 | `legs.<leg>.cylinder.bore_diameter_m` 0.13 / 0.11 |
| `actuator.rod_diameter_m`(157) | 0.11 | `legs.<leg>.cylinder.rod_diameter_m` 0.11 / 0.09 |
| `actuator.barrel_outer_diameter_m`(158) | 0.16 | `legs.<leg>.cylinder.barrel_outer_diameter_m` 0.16 / 0.137 |
| `actuator.annulus_area_m2`(165) | 8.83572934×10⁻⁴ m² | `legs.<leg>.cylinder.annulus_area_m2` 3.76991118×10⁻³ / 3.14159265×10⁻³ |
| `actuator.max_force_extend_N`(168) | 218,124.705 | `legs.<leg>.cylinder.max_force_extend_N` 278,737.808 / 199,569.673 |
| `actuator.max_force_retract_N`(169) | 18,555.0316 | `legs.<leg>.cylinder.max_force_retract_N` 79,168.1349 / 65,973.4457 |
| `actuator.rod_side_chamber_model`(166) | "neglected (head side only); …" | `actuator.rod_side`(L1-R), L2b 법칙 |

**소비 코드 전수 조사**(Grep, `03_src`·`04_scripts`·`05_tests`, 2026-10-25). 판정: 무조건 읽음 = 키를 지우면 KeyError/ParamsError, 대체 경로 = 다리별 키가 없을 때만 읽음.

| 파일:줄 | 읽는 키 | 방식 | 지우면 | 담당 |
|---|---|---|---|---|
| `03_src/outrigger_sim/sensors/hydraulic.py:56-57, 82-84, 96, 110` | bore, annulus | **무조건**(`leg_head_areas_from_params`가 96행에서 공통값을 먼저 계산, 110행도 같음) | C2·truth·rod_chamber_link·l1_scope·s6_bundle_c·run_S6·s6_stage2 전부 실패 | python |
| `03_src/outrigger_sim/chrono/rod_chamber_link.py:275-276` | bore, rod | **무조건** | L1-R 훅 생성 실패 | python |
| `03_src/outrigger_sim/chrono/actuators.py:197-210` | max_force_* | 대체 경로(try/except) | 영향 없음 | python(정리 선택) |
| `03_src/outrigger_sim/verify/s6_control.py:1277-1287` | (hydraulic 경유) | 대체 경로 | hydraulic.py 고치면 없음 | — |
| `03_src/outrigger_sim/params.py:81` | rod_side_chamber_model | TEXT_KEYS 목록만 | 영향 없음(정리 선택) | python |
| `03_src/outrigger_sim/chrono/probes.py:27`, `chrono/truth.py:29`, `actuators.py:336` | — | docstring | — | python |
| `05_tests/unit/test_hydraulic_sensors.py:35-41` | bore(현 YAML) | **무조건**, 옛 값 0.115·363,541 N을 단언 | 실패 | python |
| `05_tests/unit/test_hydraulic_sensors.py:259`, `test_s6_judge_rev10.py:365` | — | 가짜 객체(대체 경로 시험) | 영향 없음 | — |
| `05_tests/chrono/test_rod_chamber_link.py:302-308` | max_force_extend | 대체 경로(except) | 영향 없음 | — |
| `04_scripts/01_dynamics/run_target_envelope.py:185` | `actuator.rod_diameter_m` | **무조건** | KeyError. **현재도 결함**: 로드 응력 여유(207행 `P/A_r + M/Z_r`)를 네 다리 모두 ø110으로 계산한다. 후방 실제 ø90은 $A$ 0.669배, $Z$ 0.548배라 후방 로드 응력을 최대 1.82배 과소평가한다 | dynamics |
| `04_scripts/01_dynamics/dyn_model.py:666-680` | 공통 키 | 대체 경로(`act.get(key, ASSUMPTIONS)`) | 영향 없음 | — |
| `04_scripts/01_dynamics/run_s6_check.py:95-97` | bore | **정정(2026-10-25 무결성 점검)**: `.get(key, act["bore_diameter_m"])`는 기본값 인자가 먼저 평가돼 공통 키가 없으면 KeyError다. 대체 경로가 아니라 무조건 읽기였다 | dynamics가 `.get(key) or act[...]`로 고침(D-1~D-3 작업) | dyn |
| `04_scripts/00_cad/leg_rod_lateral_check.py:109-115` | 세 지름 | 대체 경로 | 영향 없음 | — |
| `04_scripts/04_hydraulic/l2_params.py:98-102` | bore, rod | **무조건**. 지금도 옛 CAD 치수 ø115/ø110으로 L2 기준을 만들면서 감쇠는 REXOME35 다리별 값(121-122행)을 섞는다 | KeyError | hydraulics |
| `04_scripts/04_hydraulic/linearize.py:33-38` | bore, rod | **무조건**, 위와 같음 | KeyError | hydraulics |
| `04_scripts/02_chrono/render_S3_gifs.py:155`, `run_target_envelope.py:85` | — | 주석·docstring | — | cad / dynamics |

권고: **삭제**. 근거: (a) `deprecated` 표시로 남기면 값이 계속 지문에 들어가고, 위 표처럼 무조건 읽는 코드가 옛 치수로 조용히 계산한다(l2_params·linearize·run_target_envelope가 실제 사례). (b) 어차피 이번 묶음에서 지문이 1회 바뀐다. 삭제를 택하면 python P-2·P-3과 dynamics D-2, hydraulics H-1이 **재생성 전에** 끝나야 한다(8절 순서).

- 대안(남김): 키를 두고 주석만 "deprecated"로 둔다. 그러면 무조건 읽는 4곳이 계속 옛 값을 쓴다. 이 대안을 고르면 적어도 hydraulic.py 96·110행의 무조건 호출은 고쳐야 한다(공통값이 다리별 값과 다르면 혼동).

**`l2_params.py`·`run_l2_reference.py`·`linearize.py` 처리안**(hydraulics 확인 필요, 위임 필요 H-1):
- (가) **이력 YAML 고정(권고)**: `load_yaml()`이 `02_params/history/rexome33_2026-10-22_before_rexome35.yaml`을 읽게 한다. L2 명세(2026-10-21 초판, 머리말에 "본문은 초판 그대로")의 수치를 같은 입력으로 재현한다. 지금처럼 옛 면적에 새 감쇠를 섞는 불일치도 없어진다.
- (나) 다리별 전환: `y["legs"][leg]["cylinder"]`에서 bore·rod를 읽는다. 결과 수치가 바뀌므로 L2 명세 재실행·재판정이 필요하다(사용자 방침상 우선순위 낮음).

### 1.4 패드 다각형·면적 → `pad_shapes` (항목 5)

스테이징 YAML의 새 최상위 블록(`legs` 다음):

```yaml
pad_shapes:
  default_type: "dwg_rear250"        # U-PAD-1
  type_order: ["cad330", "dwg_rear250"]
  types:
    cad330:      {label: "A", legs: {FL|FR|RL|RR: {source_kind, polygon_xy_m, bottom_area_m2, perimeter_m, bekker_b_m}}}
    dwg_rear250: {label: "B", legs: {...}}
```

| 타입·다리 | source_kind | 바닥 면적 [m²] | 둘레 [m] | Bekker 폭 $b=2A/\Pi$ [m] | 출처 |
|---|---|---|---|---|---|
| A 네 다리, B 전방 | `cad_brep` | 0.1071 | 1.24970563 | 0.171400364 | `01_cad/02_legs/legs/*_10_1.brep` 최저 −Y_cad 평면 |
| B 후방 RL·RR | `drawing_synthesis_brep` | 0.0607 | 0.929705627 | 0.130578967 | `01_cad/02_legs/rexome35/moving_R{L,R}.brep` 바닥면, 도면 250 × 250, 모따기 30 mm(**가정**) |

- `legs.<leg>.pad`에는 `shape`, `thickness_m`, `side_height_m`, `joint`, `swivel_center_above_pad_bottom_m`, `swivel_tilt_range_deg`가 남는다(두 타입 공통; 후방 판 두께·옆면 높이를 CAD와 같게 둔 것은 **가정**).
- 질량은 타입에 들어가지 않는다(U-PAD-3). `legs.RL/RR.moving_part`·`pad_body`는 지금처럼 250 합성이다.
- 생성 방식: 생성기가 B-rep에서 직접 계산한다(`pad_shape_from_face`, `pad_bottom_face`). `02_params/pad_variants.json`은 **읽지 않고 점검으로만 대조**한다(그 표가 YAML을 읽으므로 원본으로 쓰면 순환 의존이 생긴다).
- 점검(스테이징 실행, `rexome33_checks.json` `pad_shapes`): 꼭짓점 8개, 면 면적 대 신발끈 면적 상대차 ≤ 4.0×10⁻¹⁴, 면 무게중심 대 다리 축 ≤ 0.035 mm, 합성 후방 바닥 높이 대 CAD 패드 바닥 0.04399 mm(허용 0.05 mm, CAD_SUMMARY_TOL_MM), 후방 면적 대 $250^2-2\cdot30^2$ mm² 상대차 0, **`pad_variants.json`과 다각형 최대차 0.0 m·면적·$b$ 상대차 0**(8개 타입·다리 모두, 표 SHA-256 `698bc5e0…`). 2026-10-26 주: `698bc5e0…`은 묶음 전 표(지금 `02_params/history/pad_variants_2026-10-25_before_bundle.json`)다. C-2 뒤 표는 schema 2 C8 대응표(형상 원본은 YAML `pad_shapes`)로 바뀌었고 SHA-256은 `00cf734b…`, 그 `params_yaml.file_sha256`은 `ef2880f9…`다.
- 지문: `pad_shapes`를 L1·L2b 지문에서 빼면, 타입을 바꿔도(`default_type`을 `cad330`으로 덮어써도) L1·L2b 6개 지문이 그대로임을 계산으로 확인했다(4절 `pad_type_switch_keeps_fingerprints: true`).

**부속표 `pad_variants.json`과의 관계(권고)**: 형상 값(다각형·면적·둘레·$b$)은 YAML `pad_shapes`가 원본이 된다. `pad_variants.json`은 C8 hull·시각 OBJ 대응표(파일·SHA-256)와 C8 점검만 남기는 생성물로 줄이고, 다각형은 YAML에서 읽어 기록만 한다. `outrigger_sim/pad_variants.py`의 `apply_pad_variant`는 `legs.<leg>.pad.*` 덮어쓰기 대신 `pad_shapes.default_type` 덮어쓰기(또는 로더 인자)로 바꾼다. 이유: 지금 방식은 재생성 뒤 그대로 두면 `check_table_against_params`(`pad_variants.py:191-212`)가 **반드시 실패**한다. YAML 기본 패드가 B(후방 250)가 되는데, 표의 타입 A 후방(`cad_brep`, 330)과 비교하기 때문이다.

**SCM 실행 지문(결정 D5)**: `pad_shapes`가 L1·L2b 지문에서 빠지므로, S9(SCM) 실행·스냅숏은 자기 지문에 `pad_shapes`와 선택 타입을 넣어야 한다(5.30.5 "다른 타입 스냅숏은 맞지 않는다"를 유지). 제안: SCM 모델 종류(`ModelKind.SCM`)를 만들 때 그 지문은 `pad_shapes`를 포함하고 `"pad_type": <선택>`을 더한다. 그 전까지 S9 실행기는 meta에 타입·다각형 SHA를 남긴다(`pad_variant_meta`와 같다).

### 1.5 그 밖의 낡은 서술·키 (항목 6)

| 위치 | 옛 | 새(스테이징) | 종류 |
|---|---|---|---|
| `control.F_min_basis` | "cylinder force (pressure x bore area) = superstructure weight share; pad contact force = cylinder force + rod weight" | "net cylinder force F_cyl = p_h A_p - p_r A_ann (two pressure sensors per leg, after zero-offset calibration) = superstructure weight share; pad contact force = cylinder force + moving-part weight" | 값(지문) |
| `control.F_min_cylinder_N` 주석 | "pad contact force basis adds the rod weight, about 10.50 kN"(옛 106.78 kg·9,452.55 N 기준) | "FL 10.46 / FR 10.46 / RL 10.13 / RR 10.13 kN"(9,414.59 N + 이동부 106.78 / 73.16 kg × 9.80665 m/s², 생성기 계산) | 주석 |
| `meta.dynamics_stages.common` | 폐기 키 나열 | `legs.*.cylinder.*`, `actuator.{…, rod_dead_length_m, rod_side, pump_volumetric_efficiency, …}` | 값 |
| `meta.dynamics_stages.SCM` | pad_body, rod_body | + `pad_shapes.*` | 값 |
| `meta.sources.pad_shapes` | (없음) | 두 B-rep 출처 | 값(추가) |
| `meta.frame.origin` | "CAD origin (body origin undecided)" | "CAD origin = axis of the slewing-ring bolt circle PCD 1120 mm at the deck underside"(CLAUDE.md '좌표계와 명명') | 값 |
| `meta.mass_basis.description` | 배럴 교체 언급 없음 | "; REXOME35 barrels replace the CAD barrels (superstructure.barrel_replacement)" 추가 | 값 |
| `contact.rigid_floor.L1.derivation.damping_ratio` 주석 | "about 7.4 Hz", "(1st about 0.008)", "sqrt(kn m/4)" | "k_lock", "8.88 Hz"(`damping_reference_mode_Hz`에서 계산), 1차 로킹 ζ는 reference.json 참조 | 주석 |
| `actuator.L2b_NSC.axial_stiffness`, `actuator.L2` 주석 | "pi/4 bore^2" | `legs.<leg>.cylinder.head_area_m2` | 주석 |
| `actuator.rod_side.k_rod_side_N_m` 주석 | "annulus_area_m2" | `legs.<leg>.cylinder.annulus_area_m2` | 주석 |
| `actuator.cylinder_type` 주석 | 회로도 | + "공통 키는 2026-10-25 묶음에서 삭제" 안내 | 주석 |
| `legs.RL/RR.pad_body` 주석 | "NOTE pad.polygon_xy_m stays the CAD 330 pad (rear 250 x 250 deferred to S9)" | "the plate is the rear 250 pad of pad_shapes type B, used for both types (U-PAD-3)" | 주석 |
| `sensors` 블록 주석 | 2026-10-19 문구(현 YAML) | 두 센서·표본 주기 위치(생성기 현재판 2331행; 현 YAML이 생성기보다 오래됨) | 주석 |

점검했으나 **바꾸지 않은 것**(근거 있음):
- 680 mm 관련: `legs.*.retracted_offset_from_cad_m` 주석의 0.68은 "기하 유지 Q-C2"의 CAD 행정 추정(`CAD_RETRACT_STROKE_M`)으로 현행 정의다. `sensors.stroke.fault_threshold_m` 주석의 0.6848 m도 현행이다.
- `contact.crawler.damping_ratio_heave` 주석의 "8.1 Hz"는 다시 계산하지 않았다(질량 변화 0.4 % 수준, 확인 안 함).
- `rexome33_checks.json` 기대값: rexome35 모드의 `DOC10_EXPECTED_REX35`는 다리별 파생값과 대조하므로 공통 키 삭제와 무관하다. 스테이징 점검표는 현 점검표에 `pad_shapes` 절만 더해진다(그 밖의 차이 0).
- **기존 결함(이번 묶음 범위 밖, 기록)**: `--cylinders cad` 회귀 모드는 원본 생성기에서도 이미 실패한다(점검 2건: `doc10_printed.settle_on_pads_min_s` 차 8.28 s, `crawler.D.settle_on_crawler_min_s` 차 0.06 s). reference.json·crawler_layout_check.json이 REXOME35 기준으로 다시 만들어졌기 때문이다. 생성기 docstring의 "regression: identical except meta.generated"는 더 이상 참이 아니다. 스테이징 생성기의 cad 모드 점검표는 원본과 바이트 동일하다(바꾼 것이 cad 모드에 영향 없음).

## 2. 생성기 변경 요약 (스테이징 `export_params_staged.py`)

| 위치(스테이징 행 근처) | 변경 |
|---|---|
| docstring 69-78 | 묶음 설명 |
| 364-396 | `PRESSURE_SENSOR_LOCATION`(새) / `_CAD`(옛), `F_MIN_BASIS` / `_CAD`, `LEGACY_COMMON_CYLINDER_KEYS`, `PAD_SHAPES_DEFAULT`, `PAD_SHAPE_TYPES`, 도면 패드 상수(250, 모따기 30 **가정**), `PAD_VARIANTS_JSON`, `PAD_TABLE_TOL` 1×10⁻⁹ |
| 740-800 | `pad_shape_from_face()`, `pad_shapes_block()`(블록 + 점검) |
| 1699-1745 | 다리 반복에서 CAD·합성 바닥면 수집, rexome35 모드에서 `legs.<leg>.pad`의 다각형·면적 생략 |
| 1837-1840 | `checks["pad_shapes"]` |
| 1922-1965 | `meta.sources.pad_shapes`, `dynamics_stages`, `mass_basis.description`, `frame.origin`(모드별) |
| 2055, 2145-2170 | `pad_shapes` 블록 출력, `F_min_basis`·`location` 모드별, 폐기 키 `pop` |
| 2559-2640 | `rex35_comments(…, f_min_cylinder)`: 폐기 키 주석 제거, 새 주석 |
| 2860-2880 | `evaluate_checks` `pad_shapes` 판정 |

- `--cylinders cad` 출력은 바뀌지 않는다(점검표 바이트 동일 확인).
- 실행 시간: 원본 10.5 s(첫 실행, B-rep 읽기 포함), 스테이징 2.4 s.

## 3. YAML diff 요약 (현 `02_params/rexome33.yaml` 대 스테이징)

- diff 249줄(`yaml_diff.txt`, 스테이징 폴더). 774줄 → 853줄(`pad_shapes` 주석 포함 126줄 추가, 다리 4개 × 11줄 삭제, 공통 키 7줄 삭제).
- **수치 잎 변경 0건.** 코어스(`params._coerce_tree`) 트리 비교 결과 차이 23건:
  - 삭제 15: `actuator.{annulus_area_m2, barrel_outer_diameter_m, bore_diameter_m, max_force_extend_N, max_force_retract_N, rod_diameter_m, rod_side_chamber_model}`, `legs.{FL,FR,RL,RR}.pad.{bottom_area_m2, polygon_xy_m}`
  - 텍스트 변경 6: `control.F_min_basis`, `meta.dynamics_stages.{SCM, common}`, `meta.frame.origin`, `meta.mass_basis.description`, `sensors.cylinder_pressure.location`
  - 추가 2: `meta.sources.pad_shapes`, `pad_shapes`
- 기준 실행: 원본 생성기를 같은 방식(`--out-dir` scratch)으로 돌리면 현 YAML과 값이 같고 주석 2줄만 다르다(생성기가 YAML 생성 뒤 주석만 고쳐졌다). 현 점검표와는 바이트 동일.

## 4. 지문 영향

계산: `fingerprint_inventory.py`(스테이징 폴더). 현 YAML은 `load_params`로, 스테이징 YAML은 같은 정규화 규칙에 제안한 `TEXT_KEYS` 추가 4개와 `SCM_ONLY_HASH_PATHS`를 적용해 모사했다(모사 규칙이 현 YAML 6개 지문을 그대로 재현함을 먼저 확인: `emulation_reproduces_current: true`).

| 지문 | 현재 | 묶음 뒤(스테이징, `meta.generated` 제외라 날짜 무관) |
|---|---|---|
| `file_sha256` | `a7128d75d066650c…` | `ef2880f98aa6a20d…`(재생성 날짜·주석 sha16에 따라 다시 바뀜) |
| L1 top / middle / bottom | `de068f3b…` / `55686abc…` / `06f3ae97…` | `61078f29…` / `9845dae7…` / `5888afd5…` |
| L2b_NSC top / middle / bottom | `46684d27…` / `71beab1f…` / `6f049a86…` | `d06a97dd…` / `2f98bff1…` / `c3d52cb0…` |

- 실제 재생성 결과(2026-10-26, 동등성 기록 `yaml`·`fingerprints`): `file_sha256` `ef2880f9…`(스테이징과 같음), 6개 지문은 위 "묶음 뒤" 열과 같다.
- `pad_shapes.default_type`를 `cad330`으로 바꿔도 위 6개 지문 불변(확인).
- 주의: 생성기는 `simulation.settle_on_crawler_min_s` 주석에 crawler_layout_check.json SHA-256 앞 16자를 쓴다. 그 파일의 바이트가 바뀌면 `Params.sha256`은 그대로지만 `file_sha256`이 또 바뀐다. 그래서 dynamics 재실행(8절 5단계)을 **회귀 실행보다 먼저** 끝낸다.

## 5. 무효화되는 저장물

### 5.1 스냅숏 (`Params.sha256` 일치 필요, R16)

현재 지문과 맞는(살아 있는) 스냅숏 37개가 모두 무효가 된다. 모두 L1이다. L2b 스냅숏 중 살아 있는 것은 없다(S7 `settle_*` 3개는 이미 옛 지문).

| 폴더 | 개수 | 수준 |
|---|---|---|
| `07_results/states/S1_L1_{top,middle,bottom}.meta.json` + `.npz` | 3 | L1 |
| `07_results/states/S2b_crawler_{top,middle,bottom}` | 3 | L1 |
| `07_results/states_L1R/S1_L1_{top,middle,bottom}` | 3 | L1 |
| `07_results/states_L1R/S6_crawler_*`(bottom 6, middle 6, top 14 — `flat_L1Roff`·`flat_RRpre` 포함) | 26 | L1 |
| `07_results/S6/fdown32_L1R_20261022_131436/states/S6_crawler_bottom_fdown3.{2,5}__yaml` | 2 | L1 |
| 합 | **37**(L1 top 17·middle 9·bottom 11) | |

- 2026-10-26 정정: S6 소계는 초판의 25(top 13)가 아니라 **26(top 14)**이다(`07_results/states_L1R`의 `S6_crawler_top_*.meta.json` 14개, R1 기록 `regressions.R1.scope`). 합 37과 수준별 합은 원래 26 기준이었다.

이미 무효인 것 43개(`07_results/history_pre_rexome35_2026-10-22/states` 20, `07_results/states`의 S6 계열 14, S6 fdown32 일부 6, S7 settle 3)는 영향 없음.

### 5.2 `file_sha256`(index_guard)

- `07_results/{L1R_checks, S3, S3_L1R, S4_energy, S5, S6}/index.json` 102개 항목(2026-10-26 정정: 초판 96은 S4_energy 6을 빠뜨린 수) 중 현 YAML 파일 해시와 맞는 항목은 **이미 0개**다(2026-10-25 주석 출처 재생성 때 파일 해시가 바뀌었다). 묶음으로 새로 잃는 것은 없다. 요약 스크립트는 지금도 전부 "판정 보류"로 처리한다.
- `case.json` `run_meta.params_file_sha256`이 현 YAML과 맞는 것은 S8 8건뿐이다. `run_meta.params_sha256`이 현 지문과 맞는 것은 S3 29, S3_L1R 12, S4 12, S4_energy 6, S5 9, S6 257, S7 14, S8 53(ML 데이터 포함)이다. 묶음 뒤 이 기록들은 "물리 동일·지문 다름" 상태가 된다(7절 동등성 기록으로 처리).

### 5.3 기준해·부속표

| 파일 | 영향 |
|---|---|
| `06_analysis/00_dynamics/reference.json` | YAML 수치는 그대로라 기준값은 그대로다. 단 `dyn_model.geometry_from_params`(`dyn_model.py:120`)가 `legs.<leg>.pad.polygon_xy_m`을 읽으므로 **고치지 않으면 run_reference.py가 실패**한다. 기본 타입 B로 읽으면 `stability` 기록 필드(`run_reference.py:706-712`, `swivel=False` 강결합 지지 다각형·모서리 여유, 판정 미사용)가 후방 42.3 mm 안쪽으로 바뀐다(dynamics 계산 −2.728664 → −2.686378 m; 초판의 41.9 mm 정정) → 파일 해시가 바뀌고 index_guard가 "reference_sha differs" 경고를 낸다(경고만) |
| `06_analysis/00_dynamics/crawler_layout_check.json` | 다각형을 읽는지 dynamics 확인 필요. 재실행해 바이트가 바뀌면 YAML 주석 sha16이 바뀐다(4절 주의) |
| `02_params/pad_variants.json` | `params_yaml.file_sha256` 기록이 낡는다. `export_pad_variants.py`(347-353행 타입 A 대 YAML 다각형 대조)와 `pad_variants.check_table_against_params`가 재생성 뒤 실패한다 → 재설계(1.4절, P-5·C-2) |
| `01_cad/09_sim_shapes/sim_shapes.json` | 영향 없음(형상 파일 불변). `build_sim_shapes.py:908, 923`의 YAML 다각형 기록 필드만 후방 250으로 바뀐다 |
| `02_params/rexome33_checks.json` | `pad_shapes` 절 추가 |
| S0 벤치마크 `04_scripts/02_chrono/solver_benchmark/bench_case.py:130-131`, `make_gifs.py:185-189, 442` | `Params` 패드 면적·다각형을 쓴다. 기본 B면 후방 등가 반지름이 바뀐다(벤치마크 재현성만, 판정 무관) |

## 6. 소비 코드 변경 명세

### 6.1 python-expert (03_src, 05_tests)

| # | 파일:줄 | 변경 |
|---|---|---|
| P-1 | `03_src/outrigger_sim/params.py:48-91` | `TEXT_KEYS`에 `default_type`, `type_order`, `label`, `source_kind` 추가. `rod_side_chamber_model`(81행)은 옛 YAML(이력) 로드를 위해 남겨도 된다 |
| P-1 | `params.py:110-122, 681-719` | `SCM_ONLY_HASH_PATHS = (("pad_shapes",),)`. `parameters_sha256`은 L1·L2b 모두 이 경로를 뺀다(L1은 `L2B_ONLY_HASH_PATHS`도 뺌). **지문은 파일 트리 기준**으로 계산하고, 로더가 채운 패드 다각형을 트리에 다시 넣지 않는다(넣으면 기본 타입이 L1 지문에 들어간다) |
| P-1 | `params.py:219-228`(`Pad`), `879-886`(`_read_pad`), `889-908`(`_read_legs`) | `Pad.polygon_xy_m`·`bottom_area_m2`를 `pad_shapes.types[pad_shapes.default_type].legs[<leg>]`에서 채운다. `pad_shapes`가 없는 옛 YAML(02_params/history, `run_s6_check.py`가 씀)은 `legs.<leg>.pad.*`에서 읽는다. `Pad.pad_type: str`(또는 `Params.pad_type`)과 `perimeter_m`·`bekker_b_m`을 더하는 것을 권함. 타입 선택은 덮어쓰기 `pad_shapes.default_type`(기존 `_apply_overrides` 그대로 동작) |
| P-1 | `05_tests/unit/test_params.py:159` | 다각형 비교를 `pad_shapes` 기본 타입과 대조로. 새 시험: 타입 전환 시 L1·L2b 지문 불변, 옛 YAML(이력) 로드, 텍스트 키 |
| P-2 | `03_src/outrigger_sim/sensors/hydraulic.py:82-84, 94-104, 107-122` | 공통값은 다리별 키가 없을 때만 읽는다(96행의 무조건 `head_area_from_params`, 110행의 무조건 `params.get(ANNULUS_AREA_KEY)` 제거). `head_area_from_params`는 옛 YAML 전용(또는 FL 값)으로 docstring 정정 |
| P-2 | `05_tests/unit/test_hydraulic_sensors.py:35-41` | 현 YAML 단언을 다리별 면적(1.32732×10⁻² / 9.50332×10⁻³ m²)·잠김 힘(464,563 / 332,616 N)으로 |
| P-3 | `03_src/outrigger_sim/chrono/rod_chamber_link.py:275-283` | `common_bore`·`common_rod`를 다리별 키가 없을 때만 읽기 |
| P-4 | `03_src/outrigger_sim/chrono/actuators.py:197-210, 336`; `chrono/probes.py:27`; `chrono/truth.py:28-29` | 대체 경로 유지 가능(동작 무해). docstring에서 공통 키 언급 정리(선택) |
| P-5 | `03_src/outrigger_sim/pad_variants.py:47, 92-98, 191-246`; `chrono/sim_shapes.py:339-374` | 타입 원본을 YAML `pad_shapes`로. `apply_pad_variant` = `pad_shapes.default_type` 덮어쓰기. `check_table_against_params` 제거 또는 표 대 `pad_shapes` 대조로. C8 hull 선택은 표(C-2 뒤 구조)에서 유지. `05_tests/unit/test_pad_variants.py:39-118` 갱신 |
| P-6 | (S9 실행기, 미작성) | SCM 지문에 `pad_shapes`·선택 타입 포함(D5) |
| P-7 | `05_tests/unit/`(새) | 표본 주기 사본 일치 시험(1.2절) |
| P-8 | `05_tests/chrono/test_sim_shapes.py:91` | 주석 갱신 |

- 완료 조건: 현 YAML과 스테이징 YAML(`…\yaml_regen\staged_out\rexome33.yaml`) **둘 다**에서 `05_tests/unit` 전체 통과, 두 YAML의 L1·L2b `Params` 수치 필드(패드 다각형 제외) 동일, 스테이징 YAML 지문이 4절 표와 같음.

### 6.2 그 밖의 담당 (위임 필요)

| # | 담당 | 파일:줄 | 내용 |
|---|---|---|---|
| D-1 | dynamics | `04_scripts/01_dynamics/dyn_model.py:114-132` | `geometry_from_params`의 다각형을 `pad_shapes`(타입은 D6)에서, 옛 YAML이면 `legs.<leg>.pad`에서. `04_scripts/01_dynamics`에서 `geometry_from_params`·`polygon_xy_m`을 쓰는 파일이 `dyn_model.py` 포함 40개(Grep, 2026-10-25)라 **고치지 않으면 재생성 직후 모두 KeyError**다. 대부분 이 함수 한 곳을 거친다 |
| D-2 | dynamics | `04_scripts/01_dynamics/run_target_envelope.py:185-207` | 다리별 로드 단면(`legs.<leg>.cylinder.rod_diameter_m`). **현 결함: 후방 ø90 로드 응력을 ø110으로 계산**. 고친 뒤 목표 범위(규칙 A 포락)가 바뀌는지 재판정 필요 |
| D-3 | dynamics | `04_scripts/01_dynamics/run_pad_variant_check.py:172` | 다각형 출처 갱신(기록 스크립트) |
| D-4 | dynamics | `run_reference.py`(+ crawler layout 점검이 다각형을 읽으면 그것도) 재실행 | 8절 5단계 |
| H-1 | hydraulics | `04_scripts/04_hydraulic/l2_params.py:98-106`, `linearize.py:33-38` | 1.3절 (가) 이력 YAML 고정(권고) 또는 (나) 다리별 |
| C-1 | cad | `04_scripts/00_cad/export_params.py` | 스테이징 사본 반영, 재생성 |
| C-2 | cad | `04_scripts/00_cad/export_pad_variants.py:95-96, 254, 347-353, 384-401` | YAML `pad_shapes` 기준으로 재설계(형상은 YAML에서 읽고 C8 대응·점검만). `verify_sim_shapes.py` 재실행 |
| C-3 | cad | `04_scripts/02_chrono/solver_benchmark/bench_case.py:130-131`, `make_gifs.py:185-189, 442` | 재현용으로 `cad330` 고정(D10) |
| C-4 | cad | `04_scripts/00_cad/build_sim_shapes.py:908, 923`, `04_scripts/02_chrono/render_S3_gifs.py:155` | 기록 필드·docstring |
| M-1 | 메인 세션 | `CLAUDE.md` 기준값 표 '센서·주기' 비고 | "YAML sensors 블록의 … R6-P 전 서술이다(재생성 때 갱신 대상)" 삭제. `decision_log.md` 결정 기록, 로드맵 |

## 7. 회귀 계획

원칙: 이번 묶음은 수치를 바꾸지 않는다. 그러므로 회귀의 목적은 **(1) 지문이 바뀐 저장물을 새 지문으로 다시 만들고, (2) 결과가 비트 동일임을 보이는 것**이다. 판정을 다시 내리는 일이 아니다. 옛 스냅숏에 새 지문을 덧씌우는 재스탬프는 R16(다른 개정 결과로 대체 금지)에 어긋나므로 권하지 않는다(D8).

비용 근거: `07_results/**/case.json` `runner.job_wall_s`(`wall_times.py`, 스테이징 폴더). 벽시계는 P코어 8개 병렬(`place_process`) 기준 추정이고, 측정이 아니다. 비용 측정 실행이 아니므로 EcoQoS 해제·P 고정은 속도를 위해서만 쓴다. 짧은 시험은 E코어로 돌려도 된다.

| 단계 | 내용 | 사례 | CPU 합 | 벽시계(8 P) | 판정 |
|---|---|---|---|---|---|
| R0 | `05_tests/unit`, `05_tests/chrono`(빠른 것), `export_params.py` 점검표, `export_pad_variants --check`, `verify_sim_shapes.py` | — | 수 분 | 5~10분(`-n auto`) | 전부 통과 |
| **R1(필수)** | 스냅숏 37개 재생성: S1 L1 3수준(`run_S1.py`), S2b 크롤러 3(`run_S2b.py`), L1R S1·S6 크롤러 28(`run_S6.py`/`run_S6C.py` 스냅숏 모드, 근거 batch `snapshots_L1R_20261022_100905` 중앙 267 s, `snapshots_bundleC_*` 약 230 s), S6 fdown32 `__yaml` 2(`s6_fdown32_direct.py`, 중앙 285 s) | 37 | 약 2.5 h | **약 20~25분**(최장 약 5분 × 5파) | 새 npz 상태 배열이 옛 npz와 `np.array_equal(..., equal_nan=True)`로 같음(시각·명령 포함). 다르면 즉시 중단·보고 |
| **R2(권장)** | index 항목 재실행(index_guard가 요약에 쓰게): S3 30(근거 batch 044954 중앙 87 s, 최장 803 s), S3_L1R 12(합 1.04 h, 최장 1,079 s), L1R_checks 34(합 0.65 h), S4_energy 6(2026-10-26 추가: index_guard 대상), S5 9(합 0.07 h), S6 11(stage2_L1R급 중앙 290~590 s 가정) | 102(초판 96) | 약 4~5 h | **약 40~50분**(최장 사례 18분이 꼬리) | 각 사례 출력 시계열이 옛 사례와 비트 동일(또는 기록 자릿수 안 동일), 요약 판정 표 불변 |
| R3(선택) | S7 ctrl3 12(합 1.06 h), S8 c36 61(6.66 h)·c37 21(2.60 h) | 94(2026-10-26 주: 실제 138 = 94 + ctrl3_rerun 2 + ML 베이스 재구성 42, 7.1절) | 약 10.3 h | 약 1.4~1.6 h | S7·S8 판정 표 불변. R1·R2가 비트 동일이면 생략 권고 |
| 생략 | S8 ML 데이터(ml_main 870, 64.5 h; ml_pilot 415, 18.6 h), S0 벤치마크, S4 A_modes(131, 2.45 h) | — | — | — | 재실행하지 않고 동등성 기록으로 묶는다 |

- 권고 범위는 R0 + R1 + R2(약 1~1.5시간)였으나, **사용자 결정(2026-10-25)으로 R0 + R1 + R2 + R3**, 합 벽시계 약 2.5~3시간. 30분을 넘으므로 long-running-task-monitor 점검 규칙을 따른다.
- 동등성 기록(제안): `06_analysis/01_chrono/00_conventions/params_bundle_2026-10-25_equivalence.json`에 옛→새 지문 6쌍, 옛→새 `file_sha256`, R1·R2 비트 비교 결과, 생략한 저장물 목록을 남긴다. ML 데이터·S7·S8 기록은 이 파일로 "물리 동일"을 보인다.
- R1에서 비트 차이가 나면 원인은 소비 코드 변경(P-2·P-3의 대체 경로가 다른 값을 고름 등)이다. 회귀를 멈추고 python에 넘긴다.

### 7.1 결과 (2026-10-26)

원본은 동등성 기록 `06_analysis/01_chrono/00_conventions/params_bundle_2026-10-25_equivalence.json`(`regressions.R1`~`R3`)이다. 결정은 `decision_log.md` 2절 D8 줄에 있다. 불일치가 나면 "현재 코드 + 옛 YAML(`02_params/history/rexome33_2026-10-25_before_bundle.yaml`) + 옛 시작 상태"로 다시 돌렸다. 그 결과가 새 실행과 비트 단위로 같으면 묶음과 무관한 예외(`bundle_unrelated`)로 두고 계속했다(사용자 결정 2026-10-26).

| 단계 | 배치 | 사례 | 비트 동일 | 수용 예외(묶음 무관) | 묶음 탓 |
|---|---|---|---|---|---|
| R0 | — | unit·chrono 시험, 점검표 | R0 통과(커밋 8616be9). chrono 스냅숏 지문 실패 6건은 R1 뒤 통과(265 통과) | — | 0 |
| R1 | `07_results/params_bundle_R1_20261026_001438` | 37 | 36 | 1(`states_L1R/S6_crawler_top_flat_RRpre`, M1 전 옛 코드 산물) | 0 |
| R2 | `07_results/params_bundle_R2_20261026_011024` | 102 | 98 | 4(S3_L1R, 옛 코드 산물) | 0 |
| R3 | `07_results/params_bundle_R3_20261026_025133` | 138(S7 ctrl3 12 + ctrl3_rerun 2, S8 c36 61 + c37 21, S8 ML 베이스 재구성 42) | 4 | 134(모두 현재 코드 + 옛 YAML이 새 결과를 비트 재현) | 0 |

- R3 차이는 옛 배치(2026-10-24·25) 뒤의 코드 변경 몫이다. S7·S8 판정 표(현행 판정 코드로 옛 폴더 대 새 폴더)는 9묶음 중 4개가 같고, 나머지는 값 차이 또는 불합격 → 합격이다. 합격 → 불합격은 `S7 ctrl3 L1_PS2_fdown3.5_old_worst_nocal` 1건이다. 원인은 코드 변경이고 묶음 탓이 아니며, `s6_control_spec.md` 개정 61(298~305절)에 분석과 재실행 판정이 있다.
- S8 ML 데이터는 재실행하지 않고 동등성 기록으로 묶었다(D8).

## 8. 실행 순서 (사용자 확인 뒤)

1. 사용자 결정 D1~D11(9절).
2. python P-1~P-5(+P-7·P-8): 현 YAML과 스테이징 YAML 둘 다에서 통과.
3. dynamics D-1~D-3, hydraulics H-1.
4. cad C-1: 현 YAML·점검표를 `02_params/history/rexome33_2026-10-25_before_bundle.yaml`·`rexome33_checks_2026-10-25_before_bundle.json`으로 보관 → 스테이징 생성기를 `04_scripts/00_cad/export_params.py`로 반영 → 재생성 → 스테이징 YAML과 diff(`meta.generated` 외 0줄 기대).
5. dynamics D-4(reference.json 등 재실행) → 바이트가 바뀌면 cad가 생성기 재실행(2회 규칙) → `Params.sha256`이 4단계와 같은지 확인(`file_sha256`만 바뀔 수 있음).
6. cad C-2~C-4.
7. 회귀 R0 → R1 → R2(→ R3).
8. 문서: decision_log, CLAUDE.md(M-1), 로드맵, `cad_cylinder_vs_drawing.md` 6절 표 상태, `l2_hydraulic_model_spec.md` 머리말(hydraulics), `dynamics_model.md` 5.30.5·5.30.8 상태(dynamics).

진행(2026-10-26): 1~7단계 끝(7.1절). 8단계 문서 갱신은 2026-10-26에 했다. 대상은 이 명세 머리말·5.1·5.2·7절, CLAUDE.md M-1, 로드맵, `cad_cylinder_vs_drawing.md` 6절, `dynamics_model.md` 5.30.5·5.30.8, rev48 초안이다. decision_log D8 줄과 `l2_hydraulic_model_spec.md` 머리말은 그 전에 갱신돼 있었다.

## 9. 사용자 확인이 필요한 결정

| # | 질문 | 선택지 | 권고 |
|---|---|---|---|
| D1 | 폐기 공통 실린더 키 6개 | (가) 삭제 (나) `deprecated` 주석으로 유지 | (가). 무조건 읽는 코드 4곳이 옛 치수로 조용히 계산하는 것을 막는다 |
| D2 | `actuator.rod_side_chamber_model` | (가) 삭제 (나) 현행 문구로 바꿔 유지 | (가) |
| D3 | 표본 주기 단일 출처 | (가) YAML로 이동 (나) `c2.py` 원본 + 사본 일치 시험 | (나). 제어 주기 변경이 플랜트 스냅숏을 무효화하지 않게 |
| D4 | 패드 형상 원본 | (가) YAML `pad_shapes`가 형상 원본, `pad_variants.json`은 C8 대응표로 축소 (나) 부속표 유지(YAML은 복사본) | (가) |
| D5 | SCM 실행 지문 | (가) SCM 모델 종류의 지문에 `pad_shapes`+선택 타입 포함 (나) 실행 meta 기록만 | (가) |
| D6 | dyn_model 지지 다각형(기록용 `swivel=False`) 타입 | (가) 기본 B(reference.json 기록 필드 바뀜) (나) A 고정(reference.json 바이트 유지) | (가). 판정 미사용 필드이고 YAML 기본과 일치 |
| D7 | `l2_params.py`·`linearize.py` | (가) 이력 YAML 고정 (나) 다리별 전환 + L2 명세 재실행 | (가), hydraulics 확인 |
| D8 | 회귀 범위 | (가) R0+R1+R2 (나) +R3 (다) 재스탬프만 | 권고 (가). **결정 (나) R0~R3(사용자, 2026-10-25)**, 약 2.5~3시간 |
| D9 | `meta.frame.origin`·`mass_basis.description` 텍스트 갱신 | (가) 이번에 함께 (나) 빼기 | (가). 어차피 지문이 바뀐다 |
| D10 | S0 벤치마크 스크립트 패드 | (가) `cad330` 고정 (나) 기본 B 수용 | (가). 옛 벤치마크 재현 |
| D11 | `--cylinders cad` 회귀 모드 기존 실패 2건 | (가) docstring 정정만 (나) cad 모드 DOC10 기대값 분리 (다) cad 모드 폐지 | (가). 이번 묶음과 별개 |

별도 보고(판단 필요): `run_target_envelope.py`의 후방 로드 단면 결함(D-2)은 목표 범위 규칙 A의 근거 계산에 들어갈 수 있다. 묶음과 별개로 dynamics 판정을 먼저 받기를 권한다.

## 10. 가정

| 항목 | 값 | 종류 |
|---|---|---|
| 후방 패드 모따기 | 30 mm | 가정(도면 치수 없음, 그림 판독 25~30) |
| 후방 패드 방향 | CAD 패드 방향 3.4°(RL·RR 같은 각) | 가정(스위블) |
| 후방 판 두께·옆면 높이 | 25 / 20 mm(CAD와 같음) | 가정 |
| 회귀 벽시계 | 기존 사례 `job_wall_s` × 8 P코어 병렬 | 추정(측정 아님) |
| 비트 동일 기대 | 수치 잎 변경 0건에서 나온 기대 | 확인은 R1 |
