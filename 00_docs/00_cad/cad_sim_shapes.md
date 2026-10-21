# C8 Chrono 시각화·충돌 형상 (2026-10-21)

로드맵 4절 CAD 표 C8의 결과다. 패드 4개의 단순 형상, 상부체·마스트·오거·크롤러·배럴·로드의 시각화용 단순화 메시, 충돌 형상 후보(볼록 껍질, CoACD·V-HACD 볼록 분해, 상자)를 만들었다. Chrono에는 **새 모듈** `03_src/outrigger_sim/chrono/sim_shapes.py`로 붙인다. 기존 모델 파일(`model.py`, `system.py`, `ground_bushing.py` 등)은 고치지 않았다. 기본값은 **시각화만** 붙이고 접촉 모델은 그대로다(패드 구 + 지면 부싱, 크롤러 D안 구 24개, 충돌 패밀리 R14).

입력은 캐시뿐이다(STEP을 읽지 않음): `01_cad/01_parts/parts_classified.csv`(B-rep 부피·bbox), `01_cad/05_meshes/parts_mesh.npz`(BRepMesh 3 mm / 0.5 rad), `01_cad/02_legs/legs/*_10_1.brep`(다리 이동부 B-rep), `01_cad/06_brep/derived/crawler/crawler_collision.json`, `02_params/rexome33.yaml`(후퇴 오프셋·패드 값 대조).

## 1. 산출물과 재실행

| 경로 | 내용 | git |
|---|---|---|
| `01_cad/09_sim_shapes/visual/{deck,mast,auger,crawler}_lowres.obj` | 상부체 그룹 시각화 메시 | **제외**(`*_lowres.obj`, 합계 63 MB) |
| `visual/barrel_<leg>.obj`, `rod_<leg>.obj`, `pad_<leg>_cad.obj`, `pad_<leg>_simple.obj` | 배럴, 로드(로드+피스톤+보스), 패드 판+거싯 4개(B-rep 테셀레이션), 단순 패드(모따기 팔각판) | 추적 |
| `collision/*.obj` | 충돌 후보. 볼록 조각마다 OBJ 객체 `o piece_<k>` 하나 | 추적(2.7 MB) |
| `sim_shapes.json` | 색인: 좌표계, 부착 규칙, 형상별 통계, 설정, 출처(입력·스크립트 sha256) | 추적 |
| `sim_shapes_verification.json` | 검증 결과(4절) | 추적 |
| `sim_shapes_irrlicht_overview.png`, `sim_shapes_irrlicht_collision.png`, `sim_shapes_upper_roller.png`, `sim_shapes_render.json` | Irrlicht 확인 렌더(5절, 8절) | 추적 |
| `visual/upper_roller_{L,R}.obj`, `visual/crawler_no_upper_rollers_lowres.obj`, `collision/upper_roller_{L,R}_hull.obj` | 크롤러 상부 롤러(8절) | 추적 / 크롤러 변형은 제외(`*_lowres.obj`) |
| `work/*.npz`, `work/state.json`, `work/*_{coacd,vhacd}.json`, `work/upper_roller_check/*.png`, `work/*.log` | 중간 메시·상태·분해 설정 기록·겹침 점검 그림·자식 프로세스 로그(빈 로그 15개 + `decompose_big.log`) | npz(`*.npz`)·log(`01_cad/09_sim_shapes/work/*.log`) 제외, 나머지는 미지정. 로그는 `check_cache.py`도 무시한다(`IGNORED_PATTERNS`) |

```powershell
$py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
& $py -I 04_scripts\00_cad\build_sim_shapes.py            # 전 단계, E코어(16~27) 고정, 약 12분
#   단계만: --stage meshes|legs|hulls|decompose|upper_rollers|index, 분해 대상만: --only track_L_coacd ...
& $py -I -X utf8 04_scripts\00_cad\build_sim_shapes.py --stage upper_rollers index --cpu pcore  # 상부 롤러만(8절), 4 s
& $py -I 04_scripts\00_cad\verify_sim_shapes.py           # 10 s
& $py -I 04_scripts\00_cad\render_sim_shapes.py [--only overview collision upper_roller]  # Irrlicht 창이 잠깐 뜬다
& $py -I 04_scripts\00_cad\check_cache.py --write --cache 09_sim_shapes
& $py -I -m pytest -q 05_tests\chrono\test_sim_shapes.py  # 21개, 2 s
```

실행 기록(2026-10-21, E코어 16~27 + 낮은 우선순위): meshes 244 s, legs 5 s, hulls 1 s, decompose 소형 9개 227 s + 대형 6개 156 s(2 프로세스 병렬, OpenMP 6스레드씩).

## 2. 좌표계·부착 규칙

- 모든 OBJ: **기체 축**(x 전방 = +Z_cad, y 좌측 = +X_cad, z 상방 = +Y_cad), 원점 = CAD 원점, **m**, CAD 자세. 길이 mm → m(×1e-3), 회전(기체 ← CAD) `[[0,0,1],[1,0,0],[0,1,0]]`(det +1, 삼각형 방향 유지).
- 다리 형상은 **완전 수축 상태**다(CAD + `legs.<leg>.retracted_offset_from_cad_m` z, 후방 +2 mm). 오거(구동부+공구)는 CAD 위치(이동량 0)이고 로더가 `superstructure.auger_travel_m`을 z로 더한다.
- 상부체 형상: 상부체 바디(COG 프레임, 기체 축)에 프레임 오프셋 `−superstructure.mass_properties.com_m`(+오거면 travel).
- 다리 형상: 다리 이동부 바디에 오프셋 `−legs.<leg>.moving_part.com_m`(수축 무게중심). OBJ가 수축 상태이고 바디가 축을 따라 강체 이동하므로 신장량과 무관하다.
- L1에서는 로드와 패드가 한 바디라 패드 시각 형상도 로드 바디에 강결합으로 붙는다(스위블 기울기는 그려지지 않는다).
- 상부체 그룹(`parts_classified.csv` 최상위 조립): **mast** = MAST ASSY, TOPSHEAVE, LOWER GUIDE, 윈치, BACKSTAY CYL, BOOM, BOOM CYL, Hose guide arm·CYL / **auger** = DRIVE AUGER ASSY, AUGER TOOL / **crawler** = REX33-REX33 - 5J286105(다른 기종 REXOME25 하부체) / **deck** = 나머지(잭 실린더 제외) / **barrel_<leg>** = `leg_barrel`. 크롤러 트랙 분리: 연결 성분 bbox 전체가 |X_cad| > 690 mm이면 트랙(트랙 범위 690.6~1366.0 mm), 나머지는 중앙 프레임.

## 3. 형상별 결과

### 3.1 패드 (B-rep 대조, 판정: 일치)

단순 패드 = B-rep 바닥면 바깥 와이어의 팔각형(z_b)과 수직 옆면 끝(z_b + 20 mm)의 같은 팔각형, 모따기만큼(25 − 20 = 5 mm, 45°) 안쪽으로 줄인 팔각형(z_b + 25 mm)의 볼록 껍질이다. 판은 볼록하므로 이 껍질이 **B-rep 판(패드 바닥 + 25 mm 아래, `export_params.split_rod_pad`와 같은 분할)과 정확히 같다**. 삼각형 44개.

| 항목 | FL | FR | RL | RR | 기준 |
|---|---|---|---|---|---|
| 바닥면 면적(B-rep) [m²] | 0.107100 | 0.107100 | 0.107100 | 0.107100 | CLAUDE.md 0.1071, 상대차 ≤ 9×10⁻¹⁶ |
| OBJ 아래 향한 면적 / B-rep | −5.7×10⁻⁷ | −5.7×10⁻⁷ | +3.0×10⁻⁷ | +3.0×10⁻⁷ | OBJ 좌표 6자리(1 µm) 반올림 |
| 바깥 법선(기체) | (0, 0, −1), 기울기 0° | 같음 | 같음 | 같음 | |
| 정사각형 변 방향(기체 x에서) [°] | 47.1297 | 47.1297 | 3.3764 | 3.3764 | YAML 다각형 47.1297 / 3.3764(차 < 1×10⁻⁷°), CLAUDE.md 47.1 / 3.4 |
| 바닥 중심 − YAML `pad_bottom_center_retracted_m` [mm] | (−0.036, −0.036, 0) | (−0.036, +0.036, 0) | (0, −0.033, −0.044) | (0, +0.033, −0.044) | YAML이 0.1 mm로 반올림됨 |
| 부피 / 무게중심 / 관성(단위 밀도) vs B-rep 판 | 메모리 4×10⁻¹⁵ / 2×10⁻¹⁵ m / 3×10⁻¹³, OBJ 왕복 ≤ 4.7×10⁻⁷ / 2.2×10⁻⁷ m / 1.25×10⁻⁶ | | | | 정확(반올림만) |
| 관성 유효성 | 대칭·양정치·삼각부등식 통과(주관성 2.35, 2.35, 4.67 ×10⁻⁵ m⁵) | | | | |

### 3.2 다리 로드·패드 판(B-rep 테셀레이션 0.2 mm / 0.2 rad + 2차 감축 ≤ 0.2 %)

| 형상 | 삼각형 | 부피 vs B-rep | 무게중심 차 | 관성 상대차 | bbox 차 | 판정 |
|---|---|---|---|---|---|---|
| `rod_<leg>` (로드+피스톤+보스) | 914 | −0.18 % | 0.11~0.12 mm | 2.2×10⁻³ | 0.09~0.11 mm | 허용 일치 |
| `pad_<leg>_cad` (판 + 거싯 4) | 146 | ≤ 5.6×10⁻⁷ | ≤ 1.8×10⁻⁷ m | ≤ 1.5×10⁻⁶ | 0 | 일치 |

YAML `moving_part.com_m`와 B-rep 이동부 무게중심 차 ≤ 3.1×10⁻⁹ m(부착 오프셋 근거 확인).

### 3.3 상부체 시각화 메시 (표시 전용, 질량에 쓰지 않음)

방법: 3 mm 테셀레이션의 연결 성분마다 ① bbox 대각선 < 40 mm 성분(볼트·너트·와셔) 버림, ② 2차 오차 감축(fast-simplification)을 가장 강한 감축률부터 시도해 성분 부피 변화 ≤ 5 %·bbox ≤ 10 mm면 채택, ③ 실패하고 2,000면 이상이면 정점 군집(20/10/5 mm, 같은 기준) ④ 아니면 원본 유지.

| 그룹 | 원 메시 삼각형 | 단순화 | 비율 | 원 메시 부피 vs B-rep | 단순화 부피 vs B-rep | bbox 차 [mm] | 버린 성분 | OBJ |
|---|---|---|---|---|---|---|---|---|
| deck | 498,548 | 221,095 | 0.44 | −2.11 % | −2.34 % | 4.7 | 682 | 7.7 MB |
| mast | 238,424 | 97,943 | 0.41 | −0.17 % | −0.18 % | 5.2 | 484 | 3.4 MB |
| auger | 890,844 | 318,585 | 0.36 | **−10.2 %** | **−15.6 %** | 0.9 | 1,032 | 11.3 MB |
| crawler | 4,781,830 | 1,077,350 | 0.23 | −0.21 % | −1.12 % | 1.6 | 5,396 | 40.8 MB |
| └ 트랙 L / R | 2,350,899 / 2,334,157 | 528,025 / 534,307 | | +0.79 / −0.25 % | −0.28 / −1.16 % | 5.4 / 5.4 | | |
| barrel_FL·FR | 1,966 | 688 | 0.35 | −0.32 % | −0.43 % | 0.9 | 0 | 19 kB |
| barrel_RL·RR | 1,758 | 350 | 0.20 | −0.33 % | **−3.49 %** | 5.3 | 0 | 9 kB |

- 부피 판정(1 % 허용): mast·barrel_FL·FR 허용, deck·auger·crawler(−1.12 %)·barrel_RL·RR 불일치. 표시 전용이라 그대로 두었다. auger는 **원 메시(05_meshes)부터 −10.2 %**(BRepMesh가 일부 면을 건너뜀)라 단순화 탓이 아니다. 후방 배럴 −3.5 %는 2차 감축이 얇은 브래킷을 줄인 것이다.
- 2차 감축은 얇은 판·분리된 솔리드에서 일찍 멈춘다(메모리 기록과 같음). 합계 약 172만 삼각형이며 Irrlicht 7프레임 렌더가 0.15~0.22 s였다(5절).

### 3.4 충돌 형상 후보 (기본 미사용)

| 후보 | 종류 | 조각 | 삼각형 | 부피 / B-rep | bbox 초과 | 시간 |
|---|---|---|---|---|---|---|
| `pad_<leg>_hull` | 볼록 껍질 = 단순 패드 | 1 | 44 | 1.000 | 0 | — |
| `pad_<leg>_box` | 상자(330×330×25 mm, 변 방향 회전) | 1 | — | 바닥 면적 +1.7 %(모따기 무시) | — | — |
| `pad_<leg>_coacd` (판+거싯) | CoACD thr 0.02 | 16 / 17 / 32 / 31 | 6,108~8,820 | 1.10~1.13 | 1.2 mm | 64~98 s |
| `pad_FL_vhacd` | V-HACD | 16 | 378 | 1.07 | 0 | 1 s |
| `moving_<leg>_coacd` (로드+판+거싯) | CoACD thr 0.03 | 11 / 11 / 13 / 11 | 5,052~6,862 | 1.21 | 2.9 mm | 21~24 s |
| `rod_<leg>_hull` | 볼록 껍질 | 1 | 306~310 | 1.59 | 0.1 mm | — |
| `track_{L,R}_hull` | 볼록 껍질 | 1 | 1,834 / 1,864 | 3.67 | 0.8 / 1.6 mm | — |
| `track_{L,R}_box` | 상자(`crawler_collision.json`) | 1 | — | 4.19 | 0 | — |
| `track_{L,R}_coacd` | CoACD thr 0.05, 최대 32 | 32 | 6,608 / 6,386 | 3.03 / 3.01 | 16 mm | 55 / 52 s |
| `track_L_vhacd` | V-HACD 최대 32 | 32 | 1,248 | 2.69 | 0 | 3 s |
| `deck_coacd` / `mast_coacd` / `auger_coacd` | CoACD thr 0.08, 최대 32 | 32 / 6 / 16 | 4,794 / 1,378 / 4,564 | 7.7 / 10.5 / 2.9 | 24 / 45 / 20 mm | 92 / 9 / 24 s |
| `deck_hull` / `mast_hull` / `auger_hull` | 볼록 껍질 | 1 | 286 / 358 / 396 | 13.1 / 24.3 / 5.2 | ≤ 4.7 mm | — |

- 트랙 분해가 B-rep 부피의 약 3배인 것은 CoACD 전처리(복셀 재메시, 해상도 60)가 트랙 고리 안쪽 공간을 메우기 때문이다. 접지에 중요한 바닥면(그라우저 끝)은 덮지만, 끝 슈 틈(2.2~21.5 mm)과 롤러 위치 하중 경로는 표현하지 못한다. 상부체(deck·mast·auger) 분해는 조각이 거칠어(mast 6조각) **참고용**이다. 상부체는 레벨링 시나리오에서 지면에 닿지 않는다.
- CoACD `max_ch_vertex` 64는 `decimate=False`라 적용되지 않았다(조각당 꼭짓점 최대 902개). Bullet 볼록 껍질로는 문제없지만 조각 꼭짓점을 줄이려면 `decimate=True`로 다시 만든다.
- 각 조각은 볼록(부피 = 자기 껍질 부피, OBJ 반올림으로 상대차 ≤ 8.5×10⁻⁶)이다.

## 4. 검증 (`verify_sim_shapes.py` → `sim_shapes_verification.json`)

OBJ를 다시 읽어 계산했다. 결과: **패드·로드·충돌 후보 실패 0건**. 상부체 시각 메시의 부피 판정은 3.3절 표와 같다.

| 항목 | 기준 | 결과 |
|---|---|---|
| 파일·개수 | 색인의 꼭짓점·삼각형·조각 수와 같음 | 전부 같음 |
| 패드 면적·법선·변 방향·바닥 높이 | 3.1절 | 통과 |
| 단순 패드 vs B-rep 판 | OBJ 왕복 부피·관성 ≤ 1×10⁻⁵, 무게중심 ≤ 1 µm(6자리 반올림) | 통과(메모리 값은 10⁻¹³) |
| 로드·패드 판 메시 vs B-rep | 부피 ≤ 1 %, 무게중심 bbox 안 | 통과 |
| 충돌 조각 볼록성 | ≤ 1×10⁻⁴ | 최대 8.5×10⁻⁶ |
| 조각의 B-rep bbox 초과 | ≤ 50 mm | 최대 45 mm(mast_coacd) |
| `test_sim_shapes.py` | 21개 | 통과(2.1 s, 상부 롤러 6개 추가 — 8절): 수준 3개 오프셋, 신장 0/0.3 m·자세 회전에서 패드 바닥 = YAML 패드 바닥(0.1 mm), 시각 형상이 질량·충돌 모델을 바꾸지 않음, 충돌 옵션은 명시할 때만·시스템 추가 전에만, 상자 프리미티브 위치 |

## 5. 확인 렌더 (Irrlicht, `render_sim_shapes.py`)

- `01_cad/09_sim_shapes/sim_shapes_irrlicht_overview.png`: `L1Model(params)`(상단, 운용 신장량, 패드 접지 직전) + `attach_model_visuals`. 오거가 상단 위치(+2.996 m)로 올라가 있다. 시뮬레이션 스텝은 돌리지 않았다.
- `01_cad/09_sim_shapes/sim_shapes_irrlicht_collision.png`: 앞 왼쪽 근접. 트랙 CoACD 조각(45 % 불투명), 패드 껍질(초록), 현재 접촉 구(빨강: 크롤러 D안 24개, 패드 구 4개 — 패드 구는 판 안쪽이라 가려진다).
- Irrlicht는 pychrono 10에서 오프스크린이 없어 창이 5프레임 동안 뜬다(기본 드라이버 실패 → OpenGL 폴백 메시지). 모델 생성 + 부착 1.8 s(OBJ 읽기 포함), 렌더 0.15~0.22 s.

## 6. Chrono 연결 명세 (기존 파일은 고치지 않음)

> **충돌 형상 용도 판정(dyn 개정 20, 2026-10-21, [dynamics_model.md](../01_dynamics/dynamics_model.md) 3.11.5절)**: 강체 지면 S1~S8(L1·L2b-NSC)은 기본 접촉(패드 구 + 지면 부싱, 크롤러 D안 구)을 유지하고, 이 문서의 충돌 형상은 **시각화·간섭 확인 전용**이다. **S9(SCM)에서만** `pad_<leg>_hull`(별도 패드 바디 + 구면 조인트, 오프셋 −`pad_body.com_m`)과 크롤러 C 포락선 상자 3개/트랙(감도 A 슈별 상자, 3.11.2절)을 접촉에 쓴다. 트랙 hull·CoACD는 접촉에 쓰지 않는다. 주행 시험 T는 궤도 템플릿 슈 형상을 쓴다.

시각화만(동역학 불변, 지금 바로 사용 가능):

```python
from outrigger_sim.chrono import sim_shapes
model = L1Model(params, ...)
sim_shapes.attach_model_visuals(model)            # 상부체 기본 8개 + 다리별 rod + pad_simple
vis = irr.ChVisualSystemIrrlicht(); vis.AttachSystem(model.system); vis.Initialize()  # 부착 뒤에 바인드
```

- 연결 위치 제안: `04_scripts/02_chrono/*` 실행 스크립트(또는 S6 runner)의 `--irrlicht` 옵션에서 모델 생성 직후 위 호출. 시각화 형상은 스냅숏(R16)·V0 인벤토리에 영향이 없다(충돌 모델·질량 불변, 시험으로 확인).
- `L1Model` 생성 + 시각 형상 부착(OBJ 63 MB 읽기 포함)이 1.8 s였다. 같은 프로세스에서 OBJ는 `lru_cache`로 한 번만 읽는다.

충돌 형상을 실제 접촉에 쓰려면(모델 변형, **V 판정이 바뀐다**):

- `L1Model.__init__`에서 바디를 `system.Add` 하기 **전에** 호출해야 한다(Bullet 바인딩). 상부체: 크롤러 구 루프 대신 `sim_shapes.attach_superstructure(sup, params, visuals=(), collision=("track_L_coacd","track_R_coacd"), material=crawler_material_values(params).make())`, 그 뒤 `set_family(sup, FAMILY_SUPERSTRUCTURE)`. 다리: 패드 구 대신 `sim_shapes.attach_leg(body, params, i, pad=None, rod=False, collision=(f"pad_{leg}_hull",), material=pad_material_values(params, i).make())`, `set_family(body, FAMILY_ROD, no_collision_with=(FAMILY_SUPERSTRUCTURE,))`.
- 주의 1: 평평한 패드 껍질을 강체 L1 로드 바디에 붙이면 스위블이 피하던 **모서리 접촉**이 되살아난다(CLAUDE.md "다리 기하", 0.13° 어긋남). 패드 껍질은 **별도 패드 바디 + 구면 조인트**(SCM용 `pad_body`/`rod_body` 분할, YAML 값 있음)에서만 의미가 있다. 이때 패드 형상의 오프셋은 `−legs.<leg>.pad_body.com_m`이어야 한다(현재 `shape_offset_m`은 이동부 무게중심 기준이므로 별도 오프셋 인자를 추가해야 한다).
- 주의 2: Bullet 볼록-평면 접촉은 접촉점이 조각당 최대 4개라 D안의 롤러 위치별 하중 경로·끝 슈 틈과 하중 분배가 달라진다. SMC 강성 `kn_per_sphere`는 구 24개 기준 값이라 그대로 쓸 수 없다.
- 지면 패치(R13)는 바디별 재질 하나만 받으므로, 크롤러 형상을 바꾸면 크롤러 스트립 범위(`CRAWLER_PATCH_MARGIN_M`)도 트랙 bbox를 덮도록 다시 정해야 한다.

## 7. 가정·한계

- 그룹 경계(mast·deck 구분)는 표시 색 구분용 규약이다. 모두 상부체 강체에 붙으므로 동역학 영향은 없다.
- 크롤러는 다른 기종(REXOME25) 하부체의 그려진 형상이다.
- 시각화 단순화 허용치(성분 부피 5 %, bbox 10 mm, 40 mm 미만 성분 버림)는 표시 목적의 가정이다.
- CoACD 1.0.14(conda) 설정(threshold 0.02~0.08, 최대 조각 32, 전처리 해상도 60~100, seed 0)과 V-HACD(vhacdx 0.1.0, 해상도 4×10⁵)는 후보 비교용 가정이다. 결과는 seed·버전에 따라 달라질 수 있다.
- 상부 롤러: 중복 판정 기준(bbox +2 mm, 꼭짓점 거리 5 mm)과 원통 프리미티브는 가정이며 회전부 질량은 원본 캐시의 추정값이다(8절).

## 8. 크롤러 상부 롤러(캐리어) (2026-10-21 추가)

CAD에 상부 롤러가 측마다 1개 있다(이전 "찾지 못함"은 정정, 원본 파생 캐시 `01_cad/06_brep/derived/crawler/crawler_upper_rollers.csv`·`parts/upper_roller_{L,R}1.bbrep`, `derive_crawler_upper_rollers.py`). 부품 = 롤러 솔리드(바퀴·축 보스·브래킷이 shrinkwrap에서 한 솔리드) + 브래킷 볼트·와셔 8개, 22.516 kg(7.85 g/cm³). 축 기체 (0.000, ±1.045, −0.33272) m, 축 방향 기체 y.

생성: `build_sim_shapes.py --stage upper_rollers index --cpu pcore`(P코어 고정, 4 s). B-rep 테셀레이션 선형 0.5 mm / 각 0.2 rad, 감축 없음.

### 8.1 시각 메시·볼록 껍질 (B-rep 대비)

| 형상 | 삼각형 | 부피 | bbox 차 | 비고 |
|---|---|---|---|---|
| `visual/upper_roller_L.obj` | 7,557 | −0.32 % | 0.087 mm | 부피는 B-rep 무게중심 기준 부호 부피(아래) |
| `visual/upper_roller_R.obj` | 7,366 | −0.39 % | 0.087 mm | |
| 롤러 솔리드만(질량 특성) | 2,434 | −0.137 % | — | 닫힌 메시. 무게중심 차 0.028 mm, 관성 Frobenius 상대차 1.5×10⁻³ |
| `collision/upper_roller_{L,R}_hull.obj` | 730 / 710 | 1.44배 | 0.087 mm | 볼록성 결함 ≤ 2.1×10⁻⁷ |

- BRepMesh가 볼트 3~4개의 모따기 원뿔면(면적 80.5 mm²)을 건너뛰어 부품 전체 메시는 닫히지 않는다. 그래서 전체 부피는 원점 의존을 줄이려고 B-rep 무게중심 기준으로 쟀고(원점 기준이면 −1 %로 보인다), 질량 특성 비교는 닫힌 롤러 솔리드로만 했다. 판정: 부피 1 % 안 → 허용 일치.
- B-rep 부피(솔리드별 GProp 합)와 원본 CSV 부피 차 1.2×10⁻¹⁰.

### 8.2 충돌 후보 (기본 미사용, 주행 시험 T용)

`sim_shapes.json` `collision.upper_roller_{L,R}_cylinders`(종류 `cylinder_set`): 롤러 솔리드의 볼록 원통면(축 ∥ X_cad, 축선 0.5 mm 안, R60·R70)을 X 구간으로 합쳐 정의했다.

| 원통 | 지름 | 폭 | 중심 기체 y [m] (L / R) |
|---|---|---|---|
| 답면 1 | 120 mm | 35.000 mm (X_cad 968.0~1003.0) | +0.98550 / −0.98550 |
| 답면 2 | 120 mm | 35.000 mm (X_cad 1087.0~1122.0) | +1.10450 / −1.10450 |
| 플랜지 | 140 mm | 79.749 mm (X_cad 1005.1~1084.9) | +1.04500 / −1.04500 |

- CSV 값과 대조: 지름 차 0, 답면 폭 차 < 1×10⁻⁹ mm, 답면 구간 차 0.0005 mm, 플랜지 폭 차 7.7×10⁻⁷ mm, 세 원통 중심이 축선 위(차 0).
- Chrono 10 원통 축은 형상 프레임 z다. 저장된 회전 (w, x, y, z) = (0.7071, −0.7071, 0, 0)이 z를 기체 +y로 돌린다(시험에서 확인).

### 8.3 중복 표시 처리 (결정)

`crawler` 시각 메시(shrinkwrap 전체)에 상부 롤러가 **이미 들어 있다**. 롤러 bbox(+2 mm) 안에 있고 모든 꼭짓점이 롤러 메시에서 5 mm 안인 crawler 메시 연결 성분을 중복으로 판정했다.

| | L | R |
|---|---|---|
| 중복 성분 / 삼각형 | 9 / 1,008 | 9 / 1,318 |
| 중복 부피 / 롤러 B-rep | −2.3 % | −2.4 % (40 mm 미만 볼트는 이미 버려져 있음) |
| bbox 안이지만 중복 아님 | 1성분(94면, 0.30×10⁶ mm³, 롤러 메시에서 최대 17.8 mm) — 브래킷 아래 받침 블록으로 보임(부품 정의 밖), crawler에 남김 | 같음(166면, 0.32×10⁶ mm³) |

- 결정: **기본은 그대로 둔다.** `crawler`(롤러 포함)를 기본 시각으로 유지하고 `upper_roller_{L,R}`·`crawler_no_upper_rollers`는 `default: false`다. `attach_model_visuals(model)`의 기본 동작과 이전 API는 바뀌지 않는다.
- 상부 롤러를 따로 그리려면 `crawler_no_upper_rollers_lowres.obj`(1,075,024면 = crawler 1,077,350 − 중복 2,326면, 부피 B-rep 대비 −1.12 %)를 함께 쓴다. `attach_model_visuals(model, upper_rollers=True)`가 이 교체를 자동으로 한다. 레벨링 모델에서는 크롤러가 상부체의 일부이므로 롤러도 **상부체 바디에 고정 시각**으로 붙는다.
- 주행 시험(T)에서 롤러를 회전 바디로 돌릴 때는 `attach_upper_rollers(roller_body, params, sides=("L",), reference_point_body_m=<롤러 바디 COG의 CAD 자세 기체 좌표>)`로 롤러 바디에 붙이고, 상부체에는 `crawler_no_upper_rollers`를 쓴다. 회전부 질량·관성(CSV 추정 17.16 kg)은 원본 캐시의 추정값이다.

### 8.4 API·시험

- `sim_shapes.attach_upper_rollers(body, params, index=None, *, sides=("L","R"), reference_point_body_m=None, visual=True, collision=(), material=None, report=None) -> AttachReport`(`report`를 주면 그 `AttachReport`에 덧붙여 돌려준다), 상수 `UPPER_ROLLER_SIDES`, `CRAWLER_WITHOUT_UPPER_ROLLERS`.
- `add_visual`/`add_collision`에 선택 인자 `offset_m`(기본은 `shape_offset_m`, 기존 호출 그대로) 추가, `add_collision`이 `cylinder_set`을 처리한다.
- `attach_model_visuals(..., upper_rollers=False)` 추가(기본 False = 이전 동작).
- 시험 6개 추가(`test_sim_shapes.py` 21개 통과): 색인·기본 제외·원통 값, 상부체 자세(이동 + 회전)에서 답면 꼭짓점이 CAD 축 둘레 R 60 mm(±0.2 mm), 별도 바디 오프셋 = −기준점, 원통 3개의 축이 기체 y·축선 위·Chrono 원통 축 z, 다른 측 충돌 이름 거부, `upper_rollers=True`일 때 crawler가 중복 제외판으로 바뀜.

### 8.5 검증·렌더

- `verify_sim_shapes.py` `upper_rollers`: 12개 점검 × 2측 통과(부피·bbox·B-rep↔CSV·롤러 솔리드 질량 특성·원통 개수·지름·폭·구간·플랜지·축선·껍질 bbox·중복 부피 ±5 %), crawler 변형 면 수 일치. 전체 실패 0건.
- 렌더 `01_cad/09_sim_shapes/sim_shapes_upper_roller.png`: 왼쪽 트랙 측면 확대. 상부 롤러(주황, 별도 형상)가 트랙 프레임 윗판의 구멍에 들어앉아 상부 체인 런 아래에 보인다. 이 시점(축 높이 + 30 mm, 바깥쪽 0.75 m)에서는 구멍 가장자리가 롤러에 가려 롤러가 판에 "박힌" 것처럼 보인다(8.6절, 착시).

### 8.6 롤러–프레임 겹침 점검 (2026-10-21, 판정: CAD 간섭 아님 · 렌더 배치 오류 아님 · 시점 착시)

질문: 렌더에서 롤러가 흰 판(트랙 프레임 윗면) 위에 박혀 보이고, 치수로도 답면 바닥 Y_cad −392.7 mm가 프레임 8 최상단 −380.1 mm보다 12.6 mm 낮다. 스크립트 `04_scripts/00_cad/check_upper_roller_overlap.py`(B-rep 캐시만 읽음, P코어 고정, 18 s)로 원인을 가렸다. 결과는 `01_cad/09_sim_shapes/upper_roller_overlap_check.{png,json}`이다.

**B-rep (CAD 전역 mm, 롤러 솔리드 234 / 오른쪽 1900)**

| 이웃 솔리드 | 최소 거리 | 공통 부피 | 비고 |
|---|---|---|---|
| 프레임 8 / 1674 | **9.18 mm** | 0 | 롤러 쪽 최근접점 (1109.1, −392.72, 0) = 답면 바닥. 프레임 **윗판에 구멍**(X_cad 1045 단면에서 Z_cad −75 … +75)이 있어 롤러 플랜지·답면이 구멍을 지난다. Z_cad 0에서는 Y −381 아래 X 855~1235 전체에 프레임 재료가 없다(분류기 격자, 5 mm 간격). 그 아래에는 경사판 두 장이 있고 롤러 아래가 비어 있다 |
| 받침판 22 / 1688 | 0 (면 접촉) | 0 | 브래킷 바닥(Y −389.72)이 받침판 윗면에 얹힘 |
| 링크 833·834 / 2499·2500 | 0 | **6.45 mm³ 씩** | 답면 꼭대기 Y −272.719(축 −332.719 + 60)와 링크 레일 하면 −272.727의 0.008 mm 겹침 = 접선 접촉(그려진 상태에서 상부 런이 롤러 위에 얹힘). `upper_run_check.json`의 "접촉 Y −272.73"과 같은 점 |
| 링크 859·860 | 1.05 mm | 0 | |
| 브래킷 볼트 / 와셔 | 0.75 mm / 0 | 0 | 볼트 구멍 틈 / 와셔 면 접촉 |
| 리브 50, 센터 프레임 1379 | 26.4 / 19.0 mm | 0 | |

- "프레임 윗면이 연속이면 12.6 mm 겹침"의 전제가 틀렸다. 윗판은 롤러 자리에서 끊겨 있다. 9.18 mm는 롤러와 그 아래 경사판 사이의 거리이고, 앞 보고(파생 캐시 작성 때)의 "9.2 mm"와 같다(정정 불필요).
- **렌더·배치:** 기본 crawler 메시 안의 롤러 덩어리와 `upper_roller_L.obj`의 꼭짓점 거리는 0.35~2.7 mm(감축 오차)다. 17.8 mm인 1성분은 받침판 22로 중복이 아니다. 이중 변환이나 오프셋 부호 오류는 없다. `attach_model_visuals(upper_rollers=True)`는 crawler를 `crawler_no_upper_rollers`로 바꾸므로 롤러가 두 번 그려지지도 않는다. 그림 (a) 기본 crawler만, (b) 교체판 + 주황 롤러에서 롤러 위치·모양이 같다.
- 렌더의 흰 판은 프레임 8 윗판(Y −380.1, 판 단면은 X_cad 1045 단면 그림)이다. 카메라가 축 높이에서 거의 수평으로 보므로 구멍의 앞·뒤 가장자리가 롤러에 가려 롤러가 판을 뚫고 박힌 것처럼 보인다. 메시 단순화가 구멍을 메우지 않았는지도 확인했다. 롤러 아래(기체 z −0.395)에서 위로 쏜 광선이 원 메시와 단순화 메시에서 같은 면(받침판 −0.3897)에 처음 닿는다.
- 고친 것: 형상·배치·API는 고치지 않았다(오류 없음). 확인 그림과 점검 스크립트를 추가했고 `check_cache.py` 규칙을 등록했다.
