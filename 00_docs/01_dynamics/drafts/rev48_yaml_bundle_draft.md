# dynamics_model.md 개정 48 초안 — YAML 재생성 묶음 dynamics 몫(D-1~D-4)과 로드 단면 결함 재판정

> 이 파일은 초안이다. 메인 세션이 `dynamics_model.md` 개정 48로 합친다(개정 47은 SCM 패드 수평 구속 검토가 쓰는 중).
> 상태(2026-10-26, YAML 묶음 8단계): D-1~D-4는 모두 끝났다(커밋 8616be9, 4절). 이 초안은 아직 `dynamics_model.md`에 합치지 않았다. 그 사이 `dynamics_model.md`의 개정 48 번호는 S9 실행기 스모크 판정(5.34)에 쓰였다. 그래서 합칠 때는 새 번호를 쓴다. 판정 요지는 `decision_log.md` 2절 "별도 결함" 줄에 있다.
> 작성 2026-10-25, dynamics-expert. 근거 명세 `00_docs/00_cad/yaml_regen_bundle_2026-10-25.md` 6.2·8절, 사용자 결정 D1~D11 모두 권고안(D6 = 기본 타입 B), decision_log 2절 끝 "run_target_envelope 결함은 dynamics 재판정".

## 머리말 한 줄(개정 이력 칸에 넣을 문안)

개정 48(2026-10-25, **YAML 재생성 묶음 dynamics 몫 D-1~D-3, 로드 단면 결함 재판정**, Chrono 실행 없음, YAML·03_src 불변): `dyn_model.geometry_from_params`가 패드 다각형을 YAML `pad_shapes`(기본 타입, D6 = B)에서, 옛 YAML이면 `legs.<leg>.pad`에서 읽는다. 현 YAML과 스테이징 YAML 둘 다에서 01_dynamics 핵심 함수·`run_reference --with-l2b`·`run_target_envelope`·`run_pad_variant_check`가 KeyError 없이 돈다. `run_target_envelope.py`가 네 다리 로드 응력을 ø110 단면 하나로 계산하던 결함(후방 실제 ø90)을 다리별 단면으로 고쳐 다시 돌렸다. **목표 수용 규칙 A(상대 + 절대 마름모 4.4°/3.2°)와 축별 상한(pitch ±3°, roll ±4°), D8 운용 한계는 바뀌지 않는다**(규칙 A 수용 3,935점 중 로드 포함 불가 0점, 최소 로드 여유 할선·C45 1.80 → 1.68, YAML·20MnV6 2.14 → 1.74, 기준 1.5). 바뀐 것은 앞들림 쪽 로드 여유 수치와, 검증 범위 앞들림 꼭짓점(바닥 3.5°)이 로드 판정 쌍에서 1.5 아래로 내려간 것이다(YAML·20MnV6 1.43). 이 값은 cad `leg_rod_lateral_check.md`(이미 다리별 단면)의 앞들림 3.5° RL 1.36(동적)과 맞는다. 결과 보관본 `06_analysis/00_dynamics/history/target_envelope_2026-10-25_before_rod_section_fix.{json,png}`, `s6_slope_boundary_check_2026-10-25_before_rod_section_fix.json`.

## 1. D-1 지지 다각형 출처 (`04_scripts/01_dynamics/dyn_model.py`)

| 항목 | 내용 |
|---|---|
| 변경 | `geometry_from_params(p, pad_type=None)`: 120행 다각형을 `pad_polygons_from_params(p, pad_type)`로 바꿨다. 새 함수 `pad_type_from_params`, `pad_shape_from_params`, `pad_polygons_from_params`, 상수 `LEGACY_PAD_TYPE = "legacy"`는 **파일 끝에 덧붙였다**. `export_params.py` `LINE_REFS`가 인용하는 행 번호(43-71, 174-352)를 지키기 위해서다. 바꾼 두 행은 행 수가 같다 |
| 출처 순서 | ① 인자 `pad_type` ② YAML `pad_shapes.default_type`(스테이징 `dwg_rear250` = 타입 B, 사용자 결정 D6 (가)) ③ `pad_shapes`가 없는 옛 YAML이면 `legs.<leg>.pad.{polygon_xy_m, bottom_area_m2}`(타입 "legacy"). 옛 YAML에 타입을 주면 KeyError로 막는다 |
| 반환 | `pad_shape_from_params`: 다각형 (8,2) [m](`pad_bottom_center_retracted_m` 기준, 기체 좌표, +z에서 반시계), `bottom_area_m2`, 있으면 `perimeter_m`·`bekker_b_m`·`source_kind`, 선택한 `type` |
| 쓰는 곳 | `Geometry.pad_polygons` → `support_polygon(geo, swivel=False)`(강체 패드 팔각 껍질, 기록용)뿐이다. `swivel=True`(판정에 쓰는 기본)는 패드 중심만 쓴다 |

**두 YAML 동작 확인**(scratchpad `dyn-run/d2/test_two_yamls.py`, dynamics-dev):

| 항목 | 현 YAML(`pad_shapes` 없음) | 스테이징 YAML(공통 실린더 키 삭제, `pad_shapes` 있음) |
|---|---|---|
| 선택 타입 | legacy | dwg_rear250(B) |
| 다각형 신발끈 면적 대 YAML 면적 | 0.1071 ×4, 상대 1.8×10⁻⁹ | 0.1071 / 0.1071 / 0.0607 / 0.0607, 상대 1.8×10⁻⁹ |
| 스테이징 타입 A 대 현 YAML 다각형 | — | 최대차 **0.0 m**(8꼭짓점 × 4다리) |
| 스테이징 타입 B 전방 대 현 YAML | — | 0.0 m |
| 강체 패드 껍질 후방 끝 x | −2.728664 m | A −2.728664 / B −2.686378 m(B가 42.3 mm 안쪽) |
| `k_rod`, 다리별 로드 지름, `F_up` | 1.9007 / 1.2723 GN/m, 0.11 / 0.09 m, 278.74 / 199.57 kN | 같음(차 0) |
| `body_with_rods`(상단, e_touch + 0.05 m) | 38,760.73 kg | 같음 |
| `leg_rod_lateral_check.static_cylinder_forces_kn` | 118.22 / 115.98 / 71.96 / 70.42 kN | 같음 |
| `run_target_envelope` Ctx + `point(top, 평지, roll 4°)` | 정상 | 정상, 행정·힘·로드 여유 차 0 |
| `run_reference.cli(["--with-l2b"])`(출력 scratch) | 프로젝트 `reference.json`과 실행 시간·npz 경로 외 차 0 | 아래 4절 |

- 정적 점검: `04_scripts/01_dynamics`에서 삭제되는 키(`actuator.{bore,rod,barrel_outer}_diameter_m, annulus_area_m2, max_force_*, rod_side_chamber_model`, `legs.<leg>.pad.{polygon_xy_m, bottom_area_m2}`)를 무조건 읽는 곳은 `dyn_model.py:120`, `run_target_envelope.py:185`, `run_pad_variant_check.py:172` 세 곳과 아래 `run_s6_check.py` 한 곳이었다. 나머지는 `dm.set_cylinders_from_params`·`dm.leg_cylinder_array`(다리별 키 우선, `.get` 대체 경로) 또는 `legs.<leg>.cylinder`만 읽는다(`l2b_reference.cyl`).
- **추가로 찾은 결함(수정)**: `run_s6_check.py:95-96`이 `.get("bore_diameter_m", act["bore_diameter_m"])`로 썼다. 기본값 인자가 먼저 평가되므로 다리별 키가 있어도 공통 키가 없으면 KeyError다(명세 1.3 표는 "대체 경로"로 분류). `... .get("bore_diameter_m") or act["bore_diameter_m"]`로 고쳤다(행 수 같음, 현 YAML 결과 불변).

## 2. D-3 `run_pad_variant_check.py`

- `--params <yaml>`·`--out <json>` 인자를 더했다(기본값 = 프로젝트 YAML·`06_analysis/00_dynamics/pad_variant_check.json`).
- `rear_edge_margin`: YAML에 `pad_shapes`가 있으면 타입 A = `cad330`, B = `dwg_rear250` 다각형을 그대로 쓴다. 없으면 옛 방식(CAD 330 다각형을 변 250/330로 축척, 모따기도 22.7 mm로 축척)이다.
- 확인: 현 YAML 출력은 저장된 `pad_variant_check.json`과 **바이트 동일**. 스테이징 YAML 출력은 한 값만 다르다: `support_polygon_rigid_hull_rear_x_m.B` −2.686806 → −2.686378 m(+0.43 mm, 축척 모따기 22.7 mm 대 B-rep 모따기 30 mm, **가정** 30 mm). 기록용 필드이고 판정에 쓰지 않는다.

## 3. D-2 로드 단면 결함 재판정 (`run_target_envelope.py`, 3.12절)

### 3.1 결함과 수정

- 결함: `Ctx.__init__`이 `actuator.rod_diameter_m`(0.110 m) 하나로 $A_r$, $Z_r$를 만들고, `rod_SF`가 네 다리 모두 $\sigma=P/A_r+M/Z_r$를 그 단면으로 계산했다. 보 데이터(레버 $a_c$, 처짐 유연도, 초기 불완전 $e_0$, 오일러 하중 $P_E$)는 `leg_rod_lateral_check.leg_case`에서 다리별 단면으로 이미 받고 있었다. 그래서 응력만 후방을 ø110으로 보아, 후방 로드 응력을 $A$로 1/0.669, $Z$로 1/0.548(최대 1.82배) 과소평가했다.
- 2026-10-22 REXOME35 재처리(개정 30 보완 6 "순서 6", `run_target_envelope --stage all` 407 s) 때 이미 결함 상태였다. 그 실행의 자체 점검 C5(보간 대 `leg_case` 직접)가 **0.81**이었다(RL·RR 1.70 대 0.94). 문서 3.12.2·8124행 표는 개정 21 값(1.0×10⁻⁶)으로 남아 있었다.
- 수정: `self.rod_D = rodg[leg]["dims"][1]`(`leg_geometry` = `legs.<leg>.cylinder.rod_diameter_m`, 옛 YAML은 공통 키), $A_{r,i}$, $Z_{r,i}$ 다리별. `meta.rod_diameter_m`, `assumptions.rod_section`을 기록한다. 그림 범례의 낡은 상수(680 mm, 218 kN, 9.45 kN)를 메타 값(700 mm, 278.7/199.6 kN, 9.41 kN)으로 바꿨다.

$$\mathrm{SF}_{rod,i}=\frac{\sigma_y}{P_i/A_{r,i}+M_i/Z_{r,i}},\qquad M_i=\frac{\lvert F_i\rvert a_{c,i}+P_i(\lvert F_i\rvert f_i+e_{0,i})}{1-P_i/P_{E,i}},\qquad A_r=\tfrac{\pi}{4}D^2,\ Z_r=\tfrac{\pi}{32}D^3$$

| 기호 | 뜻 | 단위 |
|---|---|---|
| $D$ | 로드 지름, 전방 0.110 / 후방 0.090 | m |
| $P_i$ | 다리 축력 $F_{ax}$ | N |
| $F_i$ | 로드 횡력(다리 축에 수직) | N |
| $a_{c,i}$, $f_i$, $e_{0,i}$, $P_{E,i}$ | 패킹 중심까지 레버, 단위 횡력 끝 처짐, 초기 불완전, 흔들림 오일러 하중(`leg_case`, 다리별 단면) | m, m/N, m, N |
| $\sigma_y$ | C45 305 / 20MnV6 450 MPa(**가정**, `leg_rod_lateral_check.md` 8절) | Pa |

실행: `conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_target_envelope.py`(578 s, 10 작업자 spawn, 다른 계산과 겹침). 출력 `06_analysis/00_dynamics/target_envelope.json`(SHA-256 `b005928d4cb13712…`)·`.png`. 이전 결과 `history/target_envelope_2026-10-25_before_rod_section_fix.json`(`e607f7767aa992a9…`).

### 3.2 검증

| 항목 | 결과 | 판정 |
|---|---|---|
| C5 로드 여유 보간 대 `leg_case` 직접(FL·FR·RL·RR) | 1.4668 / 0.7388 / 0.9397 / 0.9566 대 같음, 상대 **1.03×10⁻⁶**(수정 전 0.81) | 일치 |
| 로드와 무관한 지도(행정 0/20/50 mm, $F_{cyl}$ 최소·최대, 스위블, 이용률 할선·YAML, 비틀림 반폭) | 23개 격자 전부 최대 차 **0** | 일치(로드 여유는 평형에 되먹임 없음) |
| 로드 여유 지도 비 새/옛 | 0.5505~1.0(최소 = 후방 지배점, $Z$ 비 0.548과 $A$ 비 0.669 사이) | 기대대로 |
| 평형 잔차 | 1.0×10⁻³ N(전과 같음) | 일치 |
| 독립 확인: 검증 앞들림 3.5° 레벨링 끝 RL | 이 계산(준정적) 할선·C45 1.65 / YAML·20MnV6 1.43. cad `leg_rod_lateral_check.md` 5절 표(동적 최대, 다리별 단면): 1.60 / 1.36 | 동적 계수(약 ×1.05)만큼 차, 방향 일치 |
| `control` 하류(`s6_envelope_check.py`, `s6r12_envelope.py`) | 행정 지도만 읽는다 → 입력 비트 동일 | 재실행 불필요 |

### 3.3 결과: 목표 수용 규칙

| 규칙(상대 / 절대 마름모) | 받아들인 점 | 로드 포함 불가(50 mm·10 mm·가드 + 로드 쌍) 10-22 → 10-25 | 받아들인 점의 최소 로드 여유 할선·C45 / YAML·20MnV6, 10-22 → 10-25 |
|---|---|---|---|
| **규칙 A(권고·채택): (4.4, 3.2) + (4.4, 3.2)** | 3,935 | **0 → 0** | 1.80 / 2.14 → **1.68 / 1.74** |
| 상대(4.4, 3.2)만 | 9,959 | 6 → 22 | 1.47 / 2.14 → 1.38 / 1.74 |
| 상대(5.5, 3.5) + 절대(4.4, 3.2) | 4,707 | 10 → 14 | 1.38 / 1.34 → 1.38 / 1.34 |
| 기하만 상대(5.5, 3.5) | 13,289 | 255 → 543 | 1.16 / 1.34 → 1.16 / 1.34 |
| 기하 맞춤 상대(5.79, 3.70/3.75) | 14,703 | 485 → 1,072 | 1.06 / 1.25 → 1.06 / 1.25 |

- 규칙 A의 나머지 최악값(행정 642.2 mm, 최소 실린더 힘 52.5 kN, 이용률 할선 0.49 / YAML 0.66)은 바뀌지 않는다.
- 규칙 A 최소 로드 여유의 위치가 바뀌었다: **평지 목표 pitch −3°(앞들림 목표), roll −0.25°, RL**(할선·C45 1.677). 축별 상한(pitch ±3°, roll ±4°)과 규칙 A를 함께 쓴 집합에서 바닥별 최소는 다음과 같다.

| 바닥(상단) | 할선·C45 10-22 → 10-25 | YAML·20MnV6 | YAML·C45(판정 쌍 아님) |
|---|---|---|---|
| 평지(세 단계) | 1.89~1.90 → **1.68~1.69** | 2.49~2.51 → 2.36~2.38 | 1.69~1.70 → 1.60~1.61 |
| 앞내림 3.2° | 2.55 → 2.19 | 3.10 → 2.66 | 2.10 → 1.80 |
| 앞들림 3.2° | 3.44 → **1.92** | 3.15 → **1.74** | 2.14 → **1.18** |
| 좌우 ±4.4° | 2.04~2.05 → 같음 | 2.18~2.20 → 같음 | 1.48~1.49 → 같음 |
| 대각 4점 | 2.23~2.26 → 1.83~2.16 | 2.70~2.72 → 2.04~2.50 | 1.83~1.84 → 1.38~1.69 |

좌우 경사는 짧은 전방 다리(ø110)가 지배하므로 그대로다. 앞뒤 성분이 있으면 후방 다리가 지배로 넘어간다.

### 3.4 결과: 평지 축 위 로드 여유 1.5 경계(3.12.4 표 대체)

| 판정 | roll(θ = 0) | pitch(φ = 0) −(앞들림) / +(앞내림) 10-22 → 10-25 |
|---|---|---|
| 할선·C45 | ±4.86~4.91°(불변) | −4.81 / 없음(행정 밖) → **−3.36 / +4.09°** |
| YAML·20MnV6 | ±5.52~5.56°(불변) | 없음 / 없음 → **−4.05 / +3.72°** |
| D8 판정 쌍(두 쌍 모두) | ±4.86~4.91° | −4.81 / 없음 → **−3.36 / +3.72°** |
| YAML·C45(두 불확실성 모두 나쁜 쪽) | ±4.38~4.41° | −4.33 / +4.07 → **−3.21 / +3.18°** |

- 축별 상한 pitch ±3°는 판정 쌍 경계(−3.36 / +3.72°) 안에 있다. 여유는 앞들림 쪽 0.36°다(수정 전 1.8°). YAML·C45 조합으로도 ±3°는 통과한다(0.18~0.21° 여유).
- 행정 경계(50 mm·마진 0: ±5.79°, +3.70 / −3.75°)는 그대로다.
- 평지 사용자 사각형(roll ±6°, pitch ±3°)의 불가 점은 로드 포함 기준에서 527 → 544점이다(정보, 잠정 범위는 이미 폐기).
- 운용 마름모 전 바닥 교집합(로드 포함, 50 mm·10 mm·가드): roll ±0.75 → ±0.5°, pitch −0.5…+0.5 → −0.5…0°. 행정만의 교집합(roll ±1.0°, pitch ±0.5°)은 그대로다. 경사 바닥에서 고정 절대 목표는 사실상 수평뿐이라는 3.12.5 결론은 그대로다.

### 3.5 결과: 3.13 검증 범위·운용 한계의 크롤러 위 판정(`run_s6_slope_boundary_check.py --stage envelope`, 39 s)

`s6_slope_boundary_check.json`의 `envelope` 키만 다시 썼다(다른 단계 키 불변, 이전 파일 `history/s6_slope_boundary_check_2026-10-25_before_rod_section_fix.json`). 레벨링 목표 0, 50 mm 여유, 로드 판정 쌍 할선·C45 / YAML·20MnV6 / YAML·C45:

| 점(바닥) | 10-22(결함) | 10-25(수정) | 판정 쌍 1.5 |
|---|---|---|---|
| 운용 앞들림 크롤러 기준 경계(OP:pitch−, 바닥 −3.30~−3.33°), 상 / 중 / 하 | 3.22~3.28 / 2.89~2.95 / 1.96~2.00 | **1.79~1.82 / 1.60~1.63** / 1.08~1.11 | 통과 |
| 운용 앞내림(OP:pitch+, 2.91°) | 2.91~3.02 / 3.62~3.77 | 2.45~2.53 / 3.03~3.14 | 통과 |
| 운용 좌우(OP:roll+, 4.11°) | 2.28~2.31 / 2.50~2.54 | 같음 | 통과 |
| 검증 앞들림 경계(N:pitch−, 바닥 −3.52~−3.54°) | 2.89~2.94 / 2.49~2.55 | **1.61~1.63 / 1.38~1.41** / 0.93~0.95 | **미달**(YAML·20MnV6) |
| 검증 앞들림 3.5°(V:pitch−3.5) | 2.97 / 2.58 | **1.65 / 1.43** / 0.97 | **미달** |
| 검증 앞내림 경계(N:pitch+) | 2.11~2.13 / 2.49~2.52 | 1.88~1.89 / 2.21~2.23 | 통과 |
| 검증 좌우 경계(N:roll, 5.54°) | 1.35~1.36 / 1.31~1.32 | 같음 | 미달(전과 같음) |

- `feasible_50_10mm_guard_rod`가 참 → 거짓으로 바뀐 점: N:pitch−, V:pitch−3.5, V:pitch−3.6(세 단계 모두, 9점). 다른 판정 플래그 변화 없음.
- 3.13 규칙 A 상호 작용(`rule_A`): 앞들림 경계 바닥에서 로드 쌍 미달로 받아들인 목표가 중심 이동 형태 0 → 1점(목표 0), 원점 중심 5.6/3.85 형태 5 → 19점이다.
- **3.13.5 결론("운용 한계를 크롤러 위 자세로 그대로 판정해도 물리적으로 안전")은 유지된다.** 앞들림 바닥 3.29~3.33°에서 판정 쌍이 1.79~1.82 / 1.60~1.63으로 1.5 이상이다(문서의 1.82~1.86 / 1.91을 바꾼다).
- 검증 범위(시뮬레이션 검증 3.5°/5.5°)의 로드 판정 쌍 미달은 좌우만이 아니라 **앞들림도**다. 검증 범위는 운용 범위 밖이고 로드 여유는 별도 지표이므로 판정은 바뀌지 않는다. 3.13.4 "로드 쌍 미달 목표는 검증 범위 자체가 로드 기준을 넘기 때문(새 문제 아님)" 문장에 "앞들림 꼭짓점 포함(개정 48)"을 더한다. cad `leg_rod_lateral_check.md`(앞들림 3.5° RL 0.92 / 1.36, 동적)는 이미 다리별 단면으로 같은 결론이었다.

### 3.6 판정

| 질문 | 답 |
|---|---|
| 목표 범위(규칙 A + 축별 상한 pitch ±3°·roll ±4°)가 바뀌는가 | **바뀌지 않는다.** 규칙 A 수용 3,935점 모두 로드 판정 쌍 ≥ 1.5(최소 1.68 / 1.74), 축별 상한은 판정 쌍 경계 −3.36 / +3.72°, ±4.86° 안 |
| D8 운용 한계 4.4° / 3.2° | **바뀌지 않는다.** D8의 로드 근거는 cad `leg_rod_lateral_check.py`(개정 3 이후 다리별 단면)다. 이 스크립트의 결함과 무관하다. 레벨링 끝 준정적 값으로도 앞들림 3.2° 판정 쌍 1.92 / 1.74 ≥ 1.5 |
| 앞들림 3.2°(후방 로드 C45/20MnV6 가정) | 판정 쌍으로는 통과(준정적 1.92 / 1.74, 크롤러 위 판정 바닥 3.33°에서 1.79 / 1.60). 동적·H4 포함 판정은 `leg_rod_lateral_check.md`(R6 AL-R 3.12 / 3.20°, 잠정 B 3.1°)가 원본이며 이번 수정과 무관하다. **YAML·C45 조합(판정 쌍 아님)은 1.18**로 수정 전 2.14에서 크게 내려갔다. 이 조합이 실제(후방 로드가 C45, 실제 $k_t$가 YAML 쪽)라면 앞들림 3.2°는 이 준정적 모델로도 1.5 미달이다. cad 문서 3항(운용 3.2°에서 YAML·C45 RL 1.14)과 같은 결론이다 |
| CLAUDE.md 기준값 | 바꿀 것 없음(목표 범위, 레벨링 시작 조건, 앞들림 3.2° 비고 "후방 로드 소재(C45) 확인 시 앞들림 재판정" 그대로) |
| 판정 | 수정 후 계산은 `일치`(C5 1.03×10⁻⁶, 비로드 지도 차 0). 목표 범위 결정 영향 없음 |

### 3.7 문서 반영 목록(개정 48로 합칠 때)

| 위치 | 바꿀 내용 |
|---|---|
| 3.12.1 표 "실린더 힘" | 218 kN → 다리별 210 bar 한계 278.7 / 199.6 kN(개정 30 이후), $F_{min}$ 9.453 → 9.415 kN, 행정 680 → 700 mm(YAML `stroke_m`). "로드 굽힘 여유" 행에 "다리별 로드 단면(전방 ø110, 후방 ø90, 개정 48)" |
| 3.12.2 C5 행 | 1.0×10⁻⁶ 유지하되 "2026-10-22 실행은 0.81(결함), 개정 48에서 1.03×10⁻⁶" 주석 |
| 3.12.3 사용자 범위 표의 로드 열 | 개정 21 값(옛 YAML). 개정 48 값으로 바꾸거나 "개정 21 기준" 표시 |
| 3.12.4 평지 로드 1.5 경계 표 | 위 3.4 표로 대체. 문장 "pitch ±3°는 모든 쌍에서 통과" 유지(YAML·C45 ±3.18~3.22°) |
| 3.12.6 권고 규칙 표 | 위 3.3 표 1열. 첫 행 최악값: 로드 할선·C45 1.68 / YAML·20MnV6 1.74(위치 평지 pitch −3°, RL) |
| 3.13.4 준정적 표의 로드 열·마지막 문장 | 위 3.5 표, "앞들림 꼭짓점 포함" |
| 3.13.5 셋째 항목, 3.13.6 표 운용 행 | "1.82~1.86 / 1.91" → "1.79~1.82 / 1.60~1.63" |
| 검증 일람(8124행 근처) 목표 포락선 행 | C5 1.03×10⁻⁶(개정 48 재실행) |
| 스크립트 일람(8188행 근처) | `run_target_envelope.py` "다리별 로드 단면(개정 48)", `run_pad_variant_check.py` "`--params`·`--out`, `pad_shapes` 다각형(개정 48)", `dyn_model.py` "`pad_shapes` 다각형 출처(개정 48, 파일 끝 함수)" |
| 5.30.5·5.30.8 상태(명세 8절 8단계) | D-1~D-4 완료(D-4는 재생성 뒤 실행, 커밋 8616be9). **반영함(2026-10-26)**: 5.30.5·5.30.8에 묶음 완료 상태를 적었다 |

## 4. D-4 준비(재생성 뒤 실행, 2회 규칙)

**실행함(2026-10-25~26, 커밋 8616be9).** 아래는 초안 당시의 준비 기록이다. 결과는 다음과 같다(2026-10-26 확인).

- `reference.json`: 지금 SHA-256 `81c65a79…`. 묶음 전 사본은 `06_analysis/00_dynamics/history/reference_2026-10-25_before_bundle.json`·`reference_L1R_series_2026-10-25_before_bundle.npz`다. 사본 대비 차는 61개 잎이다. 그중 57개는 `stability/rigid_pad_octagon_hull (comparison)`(판정 미사용 기록, 후방 −42.3 mm)이고, 나머지 4개는 실행 시간(`meta.runtime_s` 3개, `L2b_NSC_reference_rev33.V4_NSC.wall_s`)이다. 아래 판정 기준과 같다.
- `pad_variant_check.json`: 지금 SHA-256 `b9acade9…`, 묶음 전 사본 `history/pad_variant_check_2026-10-25_before_bundle.json`.
- 재생성된 YAML `file_sha256`은 `ef2880f9…`로 스테이징과 같다. `Params.sha256`(L1 상단 `61078f29…`)도 명세 4절 표와 같다(동등성 기록 `06_analysis/01_chrono/00_conventions/params_bundle_2026-10-25_equivalence.json`).

준비 당시 문안: 명세 8절 5단계 순서(cad C-1 재생성 → dynamics D-4 → 바이트가 바뀌면 cad 생성기 재실행)를 따른다.

미리보기(scratchpad `dyn-run/d2/preview_reference.py`, `run_reference.OUT`을 scratch로 돌리고 `dm.load_params`를 지정 YAML로 바꿈, `--with-l2b`, 각 약 85 s 병렬 2개):

| 비교 | 결과 |
|---|---|
| 현 YAML 미리보기 대 프로젝트 `reference.json` | 차 5개 = 실행 시간 4개 + `series_npz` 경로 1개. `reference_L1R_series.npz` 바이트 동일 |
| 스테이징 YAML 대 현 YAML 미리보기 | 실행 시간 외 차는 **`stability / rigid_pad_octagon_hull (comparison)` 57개 잎뿐**(판정 미사용 기록). 후방 끝 모서리 여유 3.1876 → 3.1453 m(−42.3 mm), 좌우 여유 −16 mm, 전복 각 −0.05~−0.56°. L1·L1-R·L2b 기준값 차 0, npz 바이트 동일 |

명령(프로젝트 루트, 재생성된 YAML이 `02_params/rexome33.yaml`에 들어간 뒤):

```powershell
Set-Location C:\workspace\outrigger_control
$c = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
Copy-Item 06_analysis\00_dynamics\reference.json 06_analysis\00_dynamics\history\reference_2026-10-25_before_bundle.json
Copy-Item 06_analysis\00_dynamics\reference_L1R_series.npz 06_analysis\00_dynamics\history\reference_L1R_series_2026-10-25_before_bundle.npz
& $c run -n dynamics-dev python -I 04_scripts/01_dynamics/run_reference.py --with-l2b          # 약 35~85 s
# 판정: history 사본 대비 차가 meta.runtime_s 계열과 stability/rigid_pad_octagon_hull 57개뿐이고, npz 바이트 동일
& $c run -n dynamics-dev python -I 04_scripts/01_dynamics/run_pad_variant_check.py             # 3 s, B 후방 껍질 +0.43 mm 한 값만 바뀜(기록)
```

- `crawler_layout_check.json`: `run_crawler_layout_check.py`는 다각형을 읽지 않는다(`geometry_from_params`·`support_polygon`·`pad_polygons` 호출 없음, `lel.LiftModel`·`lel.events`·`rref.V`만 import). **재실행하지 않는다.** 다시 돌리면 실행 시간만 바뀌어도 바이트가 바뀌고, 생성기 주석 sha16이 따라 바뀐다(명세 4절 주의).
- `target_envelope.json`: 재생성 뒤 값이 같다(두 YAML에서 `point` 결과 차 0 확인). 다시 돌리지 않는다.
- `reference.json` 바이트가 바뀌므로 cad가 생성기를 한 번 더 돌린다(2회 규칙). `Params.sha256`은 4단계와 같아야 한다. index_guard는 "reference_sha differs" 경고만 낸다.

## 5. 가정

| 항목 | 값 | 종류 |
|---|---|---|
| 로드 항복 | C45 305 MPa, 20MnV6 450 MPa | 가정(`leg_rod_lateral_check.md` 8절, 후방 소재 미확인) |
| 로드 판정 쌍 | 할선 $k_t$·C45 ≥ 1.5 그리고 YAML $k_t$·20MnV6 ≥ 1.5 | D8 결정과 같음 |
| 후방 패드 모따기 | 30 mm | 가정(도면 치수 없음, 명세 10절) |
| 준정적 | 레벨링 끝 값, 동적 초과·H4 재설정 없음 | 3.12와 같음 |
| 질량 | 경우 C 38,400.8 kg(상부체), 운용 중량 미확인 | CLAUDE.md 기준값 |

좌표: 기체 x 전방, y 좌측, z 상방, roll > 0 좌측 위, pitch > 0 앞내림, 목표 자세 $R_z(\psi)R_y(\theta)R_x(\varphi)$(ZYX 내재). 중력 $-9.80665\,\hat z$ m/s². 힘 kN, 각 °, 길이 m/mm(표시만).
