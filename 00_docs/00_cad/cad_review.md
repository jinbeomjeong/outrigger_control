# CAD 검토: REXOME33 STEP 조립품 (2026-10-19)

대상: `REXOME33_Assy_r3(미니어쳐).stp` (630,777,519 bytes, Autodesk Inventor 2020, AP214, 2023-05-10). 원본은 읽기만 했다.

목적: 시뮬레이션 모델의 기체 제원(상부체 질량·무게중심·관성, 다리 부착점·패드 위치·스트로크)을 확정할 근거를 만든다. 아래 수치는 모두 **CAD 모델에서 뽑은 값**이다. 실기 값으로 확정하려면 마지막 절의 질문에 답이 필요하다.

## 1. 산출물과 재실행

| 파일 | 내용 |
|---|---|
| `04_scripts/00_cad/step_text_index.py` | STEP 원문을 스트리밍으로 읽는다(약 9초). 제품·재질·밀도·단위를 `01_cad/00_step/step_products.csv`, `01_cad/00_step/step_header.json`에 저장 |
| `04_scripts/00_cad/extract_parts.py` | XCAF로 계층·인스턴스 변환·형상 특성을 뽑아 `01_cad/01_parts/parts.csv`(1,214행)에 저장. 약 11분, 메모리 정점 3.7 GB. CSV가 있으면 건너뛴다(`--force`로 재생성) |
| `04_scripts/00_cad/inspect_legs.py` | 잭 실린더 8개 솔리드를 월드 좌표 BREP(`01_cad/02_legs/legs/*.brep`)과 면 표(`01_cad/02_legs/leg_faces.csv`)로 내보낸다. 약 2분, 캐시 있음. `--from-brep`은 캐시된 BREP에서 면 표만 다시 만든다(STEP 읽지 않음, 0.1초) |
| `04_scripts/00_cad/analyze_parts.py` | 캐시 표만 읽어(수 초) 판정·질량 특성·그림을 만든다: `01_cad/01_parts/parts_classified.csv`, `01_cad/01_parts/cad_summary.json`, `01_cad/01_parts/layout_views.png` |
| `04_scripts/00_cad/cad_common.py` | 공통 경로와 STEP 문자열 디코더(`\X2\…\X0\` 등) |
| `04_scripts/00_cad/build_brep_cache.py` | 전체 부품 B-rep 캐시 `01_cad/06_brep/` 생성(STEP 1회 읽기, 약 3분, 바이너리 `.bbrep`). 8절 |
| `04_scripts/00_cad/brep_cache.py` | 캐시 로더(`load_part`, `iter_instances`, `load_compound`). STEP을 읽지 않는다. 8절 |
| `04_scripts/00_cad/verify_brep_cache.py` | 캐시 검증(`parts.csv`·다리·마스트 B-rep 대조, 약 4.5분). 8절 |
| `04_scripts/00_cad/convert_brep_cache.py` | 캐시 형식 변환(바이너리 ↔ ASCII, 동일성 검증 후 전환). 8.2절 |
| `04_scripts/00_cad/derive_crawler_cache.py` | 크롤러 파생 캐시(C5·C7·C8 준비, 약 8분). 8.6절 |
| `04_scripts/00_cad/check_cache.py` | 캐시 목록 `01_cad/cache_manifest.json` 쓰기(`--write`)·점검(기본, `--full`). 8절 |

실행 순서: `python -I 04_scripts/00_cad/step_text_index.py` → `extract_parts.py` → `inspect_legs.py` → `analyze_parts.py` (인터프리터는 `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe`).

- `01_cad/01_parts/parts.csv` 열: 계층 경로(`instance_path`, 이름 디코딩), 최상위 하위조립(`top_assembly`), 제품명, 인스턴스 수, 재질·밀도(XCAF), 솔리드 수, 월드 bbox(mm), 부피(mm³), 체적 중심(mm), 단위 밀도 관성 텐서(mm⁵, 중심 기준, 월드 축), 주 원통면 반경·축.
- `01_cad/01_parts/parts_classified.csv`: 위 열에 재질 보완(`material_resolved`, `density_step_g_cm3`, `density_source`), 두 경우의 질량, `leg`(FL/FR/RL/RR), `group`(body / leg_barrel / leg_rod_pad), `is_crawler`를 더한 것.
- `01_cad/02_legs/legs/*.brep` 파일명의 `_10_`은 솔리드10(로드+패드), `_17_`은 솔리드17(배럴)이다. 한글 "솔리드"는 파일명에서 빠졌다.

## 2. 단위, 전체 치수, 좌표축

**길이 단위는 mm다.** 형상 문맥 753개가 모두 `SI_UNIT(.MILLI.,.METRE.)`을 쓴다. `CENTI METRE`와 `GRAM`은 밀도 단위(`DERIVED_UNIT`)에만 쓰인다. Inventor가 지수를 +3으로 적었지만 값(강 7.85)으로 보아 g/cm³다.

**전체 치수(모든 부품 bbox 합집합, CAD 좌표):**

| CAD 축 | 범위 (mm) | 크기 (mm) | 의미 |
|---|---|---|---|
| X | −1536.5 … +1536.5 | 3,073.1 | 폭 (좌우 대칭, X=0이 중심선) |
| Y | −1050.9 … +10437.5 | 11,488.5 | 높이 (마스트를 세운 상태) |
| Z | −3001.0 … +4033.2 | 7,034.2 | 길이 |

헤더 FILE_DESCRIPTION `11,556x7,036x3,114`는 순서대로 Y·Z·X에 해당한다. Z는 1.8 mm 차이로 맞지만, Y는 67.5 mm, X는 40.9 mm 작게 나왔다. Inventor의 범위 계산 방식이나 내보내지 않은 요소 때문일 수 있다(원인 미확인).

**축 대응 (CLAUDE.md 제안 x 전방, y 좌측, z 상방):**

| 기체 축 | CAD 축 | 근거 |
|---|---|---|
| x (전방) | +Z | FRONT JACK CYL이 Z≈+2294, REAR JACK CYL이 Z≈−2556에 있다. 마스트·오거도 +Z 쪽이고 카운터웨이트는 −Z 끝에 있다 |
| y (좌측) | +X | 오른손 좌표계: z(+Y) × x(+Z) = +X |
| z (상방) | +Y | Inventor 기본 Y-상방. 마스트(상단 시브 포함 전고 10.4 m, 마스트 본체 9.85 m)와 잭 실린더 축이 Y 방향이고, 바닥 최저점이 −Y 쪽이다 |

회전행렬(기체 ← CAD)은 `[[0,0,1],[1,0,0],[0,1,0]]`이다. `cad_summary.json`의 `*_body_m` 값은 이 축 치환만 적용했고 **원점은 CAD 원점 그대로**다. 원점을 어디에 둘지는 질문 Q6에 남겼다.

## 3. 상부체·다리 판정

### 3.1 다리(아우트리거) — 확신도: 높음

근거는 네 가지다.
1. **사용자 제공: FRONT JACK CYL = 유압 실린더(아우트리거).** `FRONT JACK CYL`은 인스턴스가 2개뿐이다. 나머지 2개는 같은 형태의 `REAR JACK CYL` 2개로 찾았다. 두 제품 모두 설명이 '1,189x330x330'으로 같고, 하위 솔리드 구성(솔리드10·솔리드17)과 로드·보어·배럴 반경이 같다.
2. **기하로 독립 확인:** 바닥 최저점(Y −1050.9)을 가진 크롤러 조립품(`REX33-REX33 - 5J286105`)을 빼고 나면 가장 낮은 하위조립 4개가 정확히 잭 실린더 4개다(Y −712.0 ×2, −699.8 ×2). 그다음은 LOWER GUIDE(−654.7), MAST(−649.0)다.
3. 네 개 모두 실린더 축이 CAD +Y(수직)이고 네 모서리에 놓였다. 위 보기는 `01_cad/01_parts/layout_views.png`.
   - 같은 3면 구성·축 범위·다리 색·무게중심 표식·지면선을 실제 메시 음영으로 그린 그림: [`01_cad/01_parts/layout_views_rendered.png`](../../01_cad/01_parts/layout_views_rendered.png). 오거는 CAD 위치(Δ 0)다. 다리 4개는 강조를 위해 다른 부품 위에 그렸다(가려져도 보이게).
   - 재생성(캐시 `01_cad/05_meshes/render_mesh.npz`만 읽음, STEP 불필요, 약 85 s): `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts/00_cad/render_layout_views.py`
   - 부품 구분용 검은 윤곽선(2026-10-20): 부품별 실루엣·경계 모서리와 인접면 각도 35° 초과 모서리만, 폭 0.4 px. 가려진 선은 면과 같은 깊이 정렬로 지운다. 화면 크기 6 px 미만 부품은 윤곽선을 생략한다. 옵션은 `--no-edges`, `--edge-angle`, `--edge-width-px`, `--edge-min-part-px`.
   - 다리 신장 애니메이션: [`01_cad/02_legs/leg_extension.gif`](../../01_cad/02_legs/leg_extension.gif). 네 다리를 동시에 0 → 680 mm(22.67 mm/s, 30 s) 펴서 패드 접지 → 크롤러 들림까지 보여 준다. 측면·정면 2개 보기, 3배속, 오거 상단. 사건 시각·자세는 `01_cad/02_legs/leg_extension_kinematics.json`에 있다.
     - 재생성(약 100 s): `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts/00_cad/render_leg_extension.py`
     - 기구학 가정: 준정적 강체이고 지면은 강체 평지(z = `ground.crawler_bottom_z_m`)다. 접촉점은 패드 바닥 중심 4개와 크롤러 접촉점(`contact.crawler.sphere_layout` D안 24점: 롤러 위치 12점은 바닥에, 끝 슈 12점은 바닥 + `end_shoe_gap_m`(2.2~21.5 mm) 높이에 둔다. 점 생성은 `04_scripts/00_cad/crawler_contact.py`)이며 모두 단방향 강체 접촉이다. 끝 슈 점은 틈이 닫힌 뒤에만 닿는다. 자세 (z, roll, pitch)는 접촉 조건 아래에서 상부체 무게중심 높이를 최소로 하는 해(선형계획, 소각)다. 패드 4개만 닿은 부정정 구간은 최소제곱으로 푼다. x·y·yaw는 고정하고, 로드 무게와 스위블 기울기는 무시한다. 결과(D안, 2026-10-20 재실행): 후방 쌍 15.040 s 접지 → 앞 롤러 줄(x 0.901 m)을 축으로 pitch → 전방 쌍 15.361 s 접지와 동시에 크롤러 들림 → 680 mm에서 크롤러 최저점 들림 331.8 mm, pitch +0.121°(앞 내림)다. 끝 슈 점은 끝까지 닿지 않는다(앞 롤러 줄 축으로 앞 끝 슈 틈 2.36 mm를 닫으려면 pitch 약 2.7°, 뒤 롤러 줄 축으로 뒤 끝 슈 2.23 mm는 약 1.6°가 필요하다. 실제 최대 pitch는 0.121°). 이전 2×9 배열(x −1.840…+1.844, 모두 바닥)에서는 앞 크롤러 끝(x 1.844 m)이 축이라 전방 접지·크롤러 들림이 15.448 s, 최종 들림 329.8 mm였다. 축이 0.94 m 뒤로 와서 전방 접지가 0.088 s 일러졌다. 후방 접지와 최종 자세는 같다.
     - 같은 D안의 유연 크롤러·패드 준정적 V4(`06_analysis/00_dynamics/reference.json` `lift_V4_compliant_crawler`의 D안 배치. 없으면 스크립트가 `crawler_layout_check.json`의 D안 값으로 대신 비교한다)와 비교하면 **접지 순서가 뒤집힌다**. 유연 모델은 크롤러 위 정착 자세가 pitch +0.169°(앞 내림, 앞 끝 슈 2점 접촉, $u_z$ −3.19 mm)라 전방 쌍이 먼저(FR 15.049 s, FL 15.051 s), 후방 쌍이 15.148 s에 닿는다. 강체 기구학은 정착 자세가 수평이라 후방이 먼저다. 강체 쪽이 후방 접지는 0.11 s 이르고 전방 접지는 0.31 s 늦으며, 크롤러 이탈(15.361 s 대 15.584 s)은 0.22 s 이르다. 같은 정지 신장량에서 크롤러 최저점 들림은 50.0 mm(유연 V4는 44.9 mm)다. 차이는 접촉 유연성(크롤러 침하, 패드 압축 약 5.5 mm)에서 온다. 그래서 V4 판정은 접지 순서가 아니라 다리별 접지 시각을 같은 배치 기준해와 비교한다(CLAUDE.md "크롤러 접촉 배치"). 비교 행은 `leg_extension_kinematics.json` `reference_comparison`에 있다.
4. 다른 `*CYL` 후보는 다리가 아니다.
   - `LOCKING CYL`/`LOCKING CYL_MIR`: 오거 조립(DRIVE AUGER ASSY) 안의 작은 실린더(로드 R10, 몸체 R32.5)다. 높이 Y≈5.3~5.7 m로 지면과 멀다.
   - `BOOM CYL`, `BACKSTAY CYL`, `Hose guide CYL`, `TOP SHEAVE CYL`: 모두 마스트·붐 계통이다.

**다리 이름 대응**(위치로 정함: 전방 = +Z, 좌측 = +X):

| 다리 | STEP 인스턴스 |
|---|---|
| FL | FRONT JACK CYL:1 |
| FR | FRONT JACK CYL:2 |
| RL | REAR JACK CYL:1 |
| RR | REAR JACK CYL:2 |

**실린더 구조**(면 단위 분석, `01_cad/02_legs/leg_faces.csv`). 각 잭은 솔리드 2개로 되어 있다.
- **솔리드17 = 배럴(바깥 실린더) + 부착 브래킷.**
  - 외경 R80(Ø160), 길이 960 mm(FL: Y −475.5…+484.5).
  - 내경 R57.5(Ø115) 보어 700 mm(FL: Y −350.5…+349.5). 하단 R55 구간은 글랜드다.
  - 측판 브래킷에 R13(Ø26) 볼트 구멍이 있고 높이 범위는 FL Y −113.5…+207.5다. 상부체에 고정되는 쪽이다.
  - 전방 잭의 측판은 45° 대각으로, 후방 잭의 측판은 축에 나란하게 안쪽(중심선 쪽)에 붙어 있어 부착 방식이 다르다.
- **솔리드10 = 로드 + 피스톤 + 패드(한 덩어리).**
  - 로드 R55(Ø110)이고, 상단에 R57.5×20 mm 피스톤 원판이 있다.
  - 하단에 팔각 패드판이 있다. 수직 옆면 높이 20 mm에 윗모서리 5 mm × 45° 모따기가 더해져 판 전체 두께는 25 mm다(2026-10-19 BREP 재측정, `02_params/rexome33.yaml`의 `pad.thickness_m`). 바닥면 면적은 0.1071 m²이고 네 다리가 같다.
  - 패드와 로드는 한 솔리드이고 구면이 없다. 모델상으로는 **스위블(볼 조인트) 패드가 아니라 강결합**이다.
- **현재 상태: 완전 수축.** 피스톤 윗면이 보어 상단과 같은 높이(FL)이거나 2 mm 아래(RL/RR)다.
- **스트로크 추정 680 mm** = 보어 700 − 피스톤 두께 20. 현재 위치에서 남은 신장량은 FL/FR 680 mm, RL/RR 678 mm다. 이 값은 모델 형상에서 뺀 기하 상한이고, 실제 유압 사양(스토퍼·쿠션 등)은 확인이 필요하다(Q2).

**다리별 위치** (CAD mm, 기체 m. 기체 좌표는 CAD 원점 기준 축 치환):

| 다리 | 실린더 축 (CAD X, Z) | 패드 바닥 높이 (CAD Y) | 패드 바닥 중심 (기체 x, y, z) [m] | 브래킷 볼트 구멍 높이 (CAD Y) |
|---|---|---|---|---|
| FL | (+1323.8, +2293.8) | −699.8 | (2.2938, +1.3238, −0.6998) | −113.5 … +207.5 |
| FR | (−1323.8, +2293.8) | −699.8 | (2.2938, −1.3238, −0.6998) | −113.5 … +207.5 |
| RL | (+1167.9, −2556.0) | −712.0 | (−2.5560, +1.1679, −0.7120) | −93.7 … +212.3 |
| RR | (−1242.9, −2556.0) | −712.0 | (−2.5560, −1.2429, −0.7120) | −93.7 … +212.3 |

z는 패드 **바닥면** 높이다. 로드+패드 이동부의 질량 중심 높이는 −0.307 m(전방) / −0.319 m(후방)다. `cad_summary.json`의 `pad_center_body_m`도 같은 의미(바닥 중심)다.

**다리 간 거리 (축 중심 기준):**

| 항목 | 값 |
|---|---|
| 전방 트랙 (FL–FR) | 2,647.6 mm |
| 후방 트랙 (RL–RR) | 2,410.8 mm |
| 휠베이스 (전–후, 좌·우 같음) | 4,849.8 mm |
| 전방 쌍 중심 | X = 0.0 (대칭) |
| 후방 쌍 중심 | X = −37.5 mm (우측으로 37.5 mm 치우침, 좌우 비대칭) |
| 네 다리 사각형 중심 | CAD (X −18.8, Z −131.1) mm → 기체 (x −0.131, y −0.019) m |

- 패드 바닥 높이는 후방이 전방보다 12.2 mm 낮다(−712.0 대 −699.8).
- **지면(크롤러 바닥) Y = −1050.9 기준으로 패드는 전방 351 mm, 후방 339 mm 떠 있다.** 즉 이 모델은 크롤러로 접지하고 아우트리거를 접은 상태다. 스트로크 680 mm를 다 쓰면 크롤러를 약 330~340 mm 들어 올릴 수 있다는 계산이 나온다(기하만으로 본 추정).

### 3.2 상부체 — 확신도: 중간

- **정의(제안):** 조립품 전체에서 **다리의 이동부(솔리드10: 로드+피스톤+패드) 4개를 뺀 나머지.**
  - 배럴과 브래킷은 상부체에 고정되므로 상부체에 넣는다(`group = body` + `leg_barrel`).
  - 다리 이동부 1개는 106.8 kg, 배럴 1개는 127.1 kg(전방) / 125.5 kg(후방)이다.
- 아우트리거가 크롤러째 들어 올리는 구조로 보여(다리가 BASE DECK 쪽에 붙어 있고 크롤러는 그 아래에 있음) 크롤러(`REX33-REX33 - 5J286105`)를 상부체에 포함했다. 크롤러가 땅에 남는 운용이면 `superstructure_without_crawler` 값을 쓴다(Q3).
- 마스트는 세운 상태(높이 10.4 m)이고 오거 공구(AUGER TOOL)가 마스트 앞 Y 4.3~8.8 m에 매달려 있다. 이 자세에서의 값이다. 마스트를 눕히거나 공구를 올리고 내리면 무게중심이 바뀐다(Q4).

주요 하위조립 질량(경우 A):

| 하위조립 | 질량 |
|---|---|
| 크롤러 | 11,271 kg |
| COUNTER WEIGHT | 7,120 kg |
| DRIVE AUGER | 4,837 kg |
| MAST | 4,329 kg |
| BASE DECK | 3,919 kg |
| BOOM | 1,276 kg |

## 4. 부피·무게중심·관성

### 4.1 재질·밀도 정보

**STEP에 재질 정보가 있다.** 부품 정의 663개에 `material name`과 `density of part`(g/cm³)가 붙어 있다.

| 재질명 | 밀도 (g/cm³) | 비고 |
|---|---|---|
| 강, 연강 | 7.85 | |
| 강철, 연강 | 7.85 | |
| 강철 | 7.85 | |
| SS400 | 7.85 | 1개는 1.0 (LOGO) |
| Steel, Mild-1 | 7.86 | |
| 고무 | 0.93 | O-링 |
| **일반** | **1.0** | Inventor 기본 재질, 자리표시 값 |

- XCAF가 재질을 읽지 못한 부품이 있었다(여러 솔리드로 된 부품, 최상위 단일 부품). 이런 부품은 STEP 원문 색인으로 보완했다.

  | 출처 | 행 수 |
  |---|---|
  | XCAF | 1,051 |
  | 같은 제품명 | 99 |
  | 부모 제품명 | 49 |
  | 판단 불가 → 강 7.85 가정 | 15 |

  가정한 15행의 질량은 합계 210 kg이다(이름 중복으로 재질이 갈리는 `부품N` 등).
- 솔리드가 없는 56행(Inventor 설계가속기 기어 자리표시, 개방 셸 등)은 질량 0으로 처리했다.

질량은 두 경우로 냈다.
- **경우 A (STEP 밀도 그대로):** '일반' 1.0을 그대로 둔다. STEP에 적힌 값을 쓰는 1차 값이다.
- **경우 B (가정치):** '일반' 1.0을 강 7.85로, 유리·창(이름에 glass/window)을 2.5로 바꾼다. **가정이다.**

### 4.2 결과 (기체 좌표, 원점 = CAD 원점, 관성은 무게중심 기준)

| 집합 | 경우 | 질량 [kg] | 무게중심 (x, y, z) [m] | Ixx, Iyy, Izz [kg·m²] | Ixy, Ixz, Iyz [kg·m²] |
|---|---|---|---|---|---|
| 전체 조립품 | A | 37,744 | (0.348, −0.002, 1.517) | 295,464 / 442,363 / 185,779 | −971 / −126,154 / −133 |
| **상부체**(다리 이동부 제외) | A | **37,317** | **(0.354, −0.002, 1.538)** | 293,282 / 438,255 / 182,481 | −948 / −125,769 / −119 |
| 상부체(크롤러도 제외) | A | 26,046 | (0.521, −0.002, 2.439) | 211,765 / 353,567 / 158,340 | −957 / −112,716 / −172 |
| 전체 조립품 | B | 42,563 | (0.385, 0.068, 1.621) | 331,144 / 490,615 / 203,456 | 1,104 / −146,424 / 1,420 |
| **상부체** | B | **42,136** | **(0.390, 0.068, 1.640)** | 328,793 / 486,325 / 200,139 | 1,143 / −145,987 / 1,492 |
| 상부체(크롤러 제외) | B | 30,865 | (0.545, 0.093, 2.438) | 243,786 / 397,879 / 175,586 | 1,588 / −131,714 / 3,790 |

- 관성 텐서는 텐서 표기다(비대각 = −∫xy dm). Ixz가 큰 것은 무거운 마스트·오거가 앞쪽 높은 곳에 있기 때문이다. 주관성모멘트는 `cad_summary.json`의 `principal_moments_kg_m2`에 있다.
- 상부체 무게중심(경우 A)을 다리 기준으로 보면 다음과 같다.
  - 네 다리 사각형 중심보다 **전방으로 0.485 m**, 좌우로는 +0.017 m.
  - 패드 바닥에서 약 **2.24 m** 위, 크롤러 바닥(지면)에서 약 2.59 m 위.
- 경우 A와 B의 차이 4.8 t의 대부분은 아래 세 부품이다. 무게중심 y가 +0.07 m 움직이는 것은 좌측에 있는 운전실 shrinkwrap 때문이다.

### 4.3 밀도 가정이 크게 틀릴 수 있는 부품

| 부품 | STEP 재질 | 질량 A → B | 문제 |
|---|---|---|---|
| `BUMA CE 3D 20230425 / 부마씨이 소구경 3D_Shrinkwrap_11` (운전실 영역, 좌측) | 일반 1.0 | 501 → 3,933 kg | 단순화(shrinkwrap) 덩어리. bbox 충전율 14%. 실제 운전실 질량을 대표하는지 불명 |
| `AUGER TOOL / TOOL ROD`, `TOOL CAP` | 일반 1.0 | 141 → 1,103 kg, 39 → 310 kg | 실물은 강재일 것. 속이 빈 로드인지 모델이 실제 단면인지 확인 필요 |
| `REX33-REX33 - 5J286105` (크롤러, 단일 바디 3,214 솔리드) | 강철 7.85 | 11,271 kg | 설명이 'REXOME25'인 외부 모델. 단순화 모델이라 실제 하부체 질량과 다를 수 있음 |
| 유리 12개(`CABIN-2 (... glass)`, `SLIDE WINDOW`) | 일반 1.0 | 합계 약 25 → 63 kg | 유리 실제 밀도는 약 2.5 |
| 순환펌프·엔코더·모터가드 등 '일반' 소형 부품 | 일반 1.0 | 합계 수십 kg | 영향 작음 |
| COUNTER WEIGHT (85개 부품, 88 솔리드) | 강, 연강 7.85 | 7,120 kg | 실물이 주철(약 7.2)이나 콘크리트 충전이면 달라짐. 판 형상은 실제 덩어리로 보임 |
| 엔진·유압탱크·연료 | (모델에 거의 없음) | — | SIDE HOUSING은 판금 커버만 있다. 엔진·펌프·작동유·연료의 질량이 빠져 있을 가능성이 크다 |

## 5. "미니어쳐"라는 이름과 치수

- 치수와 부품은 **실기 크기**로 보인다.
  - 전고 10.4 m(마스트 상단 시브 포함, 마스트 본체 9.85 m), 전장 7.0 m, 폭 3.1 m.
  - 볼트 KS B 1002 M8~M16, 베어링 JIS 32968J3(340×460×76) 같은 실제 규격품이 실물 크기로 들어 있다.
  - 질량이 수십 톤이다.
- 축소 모형이라면 표준 체결 부품이 실치수로 들어갈 이유가 없다. 따라서 "미니어쳐"는 축척이 아니라 **기종 이름(소형/소구경 천공기)이나 경량화한 내보내기본**을 뜻할 가능성이 크다(추정). 실제로 하위조립 이름에 "소구경"이 있고, 크롤러·운전실은 shrinkwrap이나 외부 모델로 단순화되어 있다.

## 6. 확인 필요 질문

1. **Q1 (질량 기준):** 실기의 운용 중량과 무게중심 자료(카탈로그·계산서)가 있는가? 모델 기준 질량은 경우 A 37.7 t, 경우 B 42.6 t이고, 엔진·작동유·연료가 빠졌을 수 있다. 기종명 "REXOME33"의 33이 중량(t)을 뜻하는지도 확인하고 싶다.
2. **Q2 (스트로크):** 잭 실린더의 사양 스트로크는? 모델 기하로는 680 mm(보어 700 − 피스톤 20)다. 신장·수축 속도(유량)도 있으면 구동기 모델에 쓴다.
3. **Q3 (지지 대상):** 레벨링할 때 아우트리거가 크롤러까지 들어 올리는가(상부체 = 크롤러 포함 37.3 t), 아니면 크롤러는 접지한 채 데크만 받치는가(26.0 t)? 크롤러와 데크 사이에 선회·서스펜션이 있는가?
4. **Q4 (작업 자세):** 시뮬레이션할 자세는 마스트를 세우고 공구를 올린 이 모델의 자세인가? 마스트를 눕힌 상태나 공구 위치가 바뀌는 경우도 다뤄야 하는가?
5. **Q5 (패드):** 실물 패드가 로드와 강결합인가, 스위블(볼 조인트)인가? 모델은 강결합(한 솔리드)이다. 연약 지면 SCM에서 접촉 형상(팔각판 0.107 m²)을 이대로 써도 되는가?
6. **Q6 (좌표계 원점):** 기체 좌표 원점을 무엇으로 할까? 후보는 CAD 원점(현재 값), 네 다리 축 사각형 중심, 상부체 무게중심이다. 축 대응(x=+Z_cad, y=+X_cad, z=+Y_cad)을 확정해도 되는가?
7. **Q7 (후방 비대칭):** 후방 다리 쌍이 37.5 mm 우측으로 치우쳐 있고(RL X +1167.9, RR X −1242.9), 후방 패드가 전방보다 12.2 mm 낮다. 설계 의도인가, 모델 오차인가?
8. **Q8 (재질):** shrinkwrap 운전실(501 kg vs 3,933 kg), 오거 공구, 크롤러의 실제 질량은? 이 세 개가 질량 불확실성의 대부분이다.
9. **Q9 (전후 구분):** FRONT/REAR 이름과 마스트 위치로 +Z를 전방으로 잡았다. 실기의 주행·작업 전방과 같은가?

## 7. 문서 반영 제안 (직접 수정하지 않음)

- `CLAUDE.md` "좌표계와 명명": CAD 축 대응(x=+Z_cad, y=+X_cad, z=+Y_cad)과 다리 대응(FL=FRONT JACK CYL:1, FR=:2, RL=REAR JACK CYL:1, RR=:2)을 추가.
- `README.md` "CAD 자료": 아우트리거 실린더 `REAR JACK CYL`×2를 추가하고 `LOCKING CYL`은 다리가 아님을 명시. (2026-10-19 반영함)
- `01_cad/` 산출물(합계 약 2.1 MB: `02_legs/legs/*.brep` 약 0.3 MB, `01_parts/parts*.csv` 약 1.5 MB)은 git으로 추적한다. 재생성에 STEP 원본과 약 11분이 필요하기 때문이다. (2026-10-20 폴더 재배치로 경로만 바뀌었다.)
- `01_cad/**/*.csv`는 엑셀 호환을 위해 UTF-8 BOM으로 저장된다. 외부 도구로 읽을 때는 `utf-8-sig`를 쓴다.

## 8. 전체 부품 B-rep 캐시와 캐시 목록 (C4·C6, 2026-10-20)

STEP(약 630 MB)을 다시 파싱하지 않고 부품 형상을 질의하려고 모든 부품을 OpenCascade 네이티브 형식으로 저장했다. 처음에는 BRepTools ASCII(`.brep`)로 만들었고, 같은 날 사용자 결정으로 **BinTools 바이너리(`.bbrep`)를 기본**으로 바꿨다(8.2절). 좌표는 CAD 루트 좌표(mm, Y-상방)다.

### 8.1 구조

| 경로 | 내용 | git |
|---|---|---|
| `01_cad/06_brep/prototypes/<entry>.bbrep` | 프로토타입(제품 정의)마다 1개, **자기 좌표계**, BinTools 형식 버전 4, 삼각망 없음. `<entry>`는 OCAF 엔트리의 `:`을 `_`로 바꾼 것(`0:1:1:375` → `0_1_1_375.bbrep`). 681개, 387.7 MB | 제외 |
| `01_cad/06_brep/instances.csv` | 말단 인스턴스 1,214행. 키 `instance_path`·`prototype_entry`는 `01_parts/parts.csv`와 같다(조인 가능). 배치 `m00…m23` = 3×4 아핀 행렬(행 우선, 전역 ← 프로토타입, mm), `scale`, `is_mirrored`, `top_assembly`, `depth`, `prototype_file`. 0.49 MB | 추적 |
| `01_cad/06_brep/prototypes.csv` | 프로토타입 681행: 파일명, 제품명, 인스턴스 수, 재질·밀도(XCAF), 솔리드·셸·면·모서리·꼭짓점 수, 파일 크기·sha256. 0.10 MB | 추적 |
| `01_cad/06_brep/cache_info.json` | 생성 설정·개수·시간·메모리·STEP 크기와 수정 시각·패키지 버전·형식 변환 기록 | 추적 |
| `01_cad/06_brep/verification.json` | 8.4절 검증 결과(바이너리 기준으로 다시 실행) | 추적 |
| `01_cad/06_brep/format_conversion.json` | ASCII → 바이너리 변환 비교(8.2절) | 추적 |
| `01_cad/06_brep/derived/crawler/` | 크롤러 파생 캐시(8.6절) | `crawler_lowres.obj`만 제외 |
| `01_cad/06_brep/**/*.log` | 진행 로그(`build.log`, `convert.log`, `derived/crawler/derive.log`) | 제외 |
| `01_cad/cache_manifest.json` | 캐시 목록(8.5절) | 추적 |

- 같은 프로토타입은 한 번만 저장한다. 인스턴스가 2개 이상인 프로토타입은 116개(최대 63개, 볼트류)다. 미러 인스턴스와 배율 ≠ 1 인스턴스는 0개다.
- 용량의 87 %(335.4 MB)는 크롤러 단순화 모델 한 개(`REX33-REX33 - 5J286105:1`, 엔트리 `0:1:1:746`, 솔리드 3,214개·면 156,614개)다. STEP 설명상 **다른 기종(REXOME25)의 하부체**다. 나머지 680개 합계는 52.3 MB다.

### 8.2 생성·변환 명령과 실행 기록

```powershell
$py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
& $py -I 04_scripts\00_cad\build_brep_cache.py [--force]          # STEP 1회 읽기, 바이너리로 저장
& $py -I 04_scripts\00_cad\convert_brep_cache.py --to ascii --keep-source   # ASCII로 전환(표가 .brep을 가리킴, 바이너리 파일은 남김)
& $py -I 04_scripts\00_cad\convert_brep_cache.py --to binary      # 바이너리로 전환(검증 통과 시 ASCII 삭제, 현재 상태)
& $py -I 04_scripts\00_cad\verify_brep_cache.py
& $py -I 04_scripts\00_cad\derive_crawler_cache.py               # 8.6절, 약 8분
& $py -I 04_scripts\00_cad\check_cache.py --write
```

- 리더 설정은 `extract_parts.py`와 같다(`load_document`, `collect_occurrences`를 그대로 쓴다). 그래서 OCAF 엔트리가 `parts.csv`와 일치한다.
- 첫 생성(2026-10-20, ASCII): STEP 읽기·XCAF 변환 125 s, 프로토타입 쓰기 63 s(파일마다 다시 읽어 꼭짓점 비교 포함), 합계 188 s, **메모리 정점 3.94 GB**. `build_brep_cache.py`는 이제 바이너리로 쓴다(이후 재생성은 같은 시간대일 것으로 본다. 바이너리 쓰기 자체는 측정하지 않음).
- 형식 변환(`convert_brep_cache.py --to binary`, STEP 읽지 않음, 103 s, 정점 2.1 GB): 681개 모두 위상 개수(솔리드·셸·면·모서리·꼭짓점) 같음, 꼭짓점 최대 차 **0 mm**, 부피 상대차 최대 9.2×10⁻¹⁶, 무게중심 2.3×10⁻¹³ mm, 관성 Frobenius 상대차 1.0×10⁻¹² → 통과 후 ASCII 파일을 지웠다.

**ASCII 대 바이너리** (읽기 시간은 프로세스를 새로 띄워 2회 측정, OS 파일 캐시는 데워진 상태)

| 대상 | ASCII 크기 | 바이너리 크기 | ASCII 읽기 | 바이너리 읽기 | 읽은 뒤 메모리 정점 |
|---|---|---|---|---|---|
| 크롤러 `0_1_1_746` | 694.8 MB | 335.4 MB (0.48배) | 9.44 / 9.51 s | 3.18 / 3.10 s (약 3.0배 빠름) | 0.96 GB (두 형식 같음) |
| 나머지 680개 합계 | 77.9 MB | 52.3 MB (0.67배) | 1.58 / 1.59 s | 0.63 / 0.64 s (약 2.5배) | 0.08 GB |
| 전체 681개 | 772.7 MB | 387.7 MB (0.50배) | 약 11.0 s | 약 3.8 s | — |

### 8.3 로더 사용법 (`04_scripts/00_cad/brep_cache.py`)

```python
import sys
sys.path.insert(0, r"C:\workspace\outrigger_control\04_scripts\00_cad")
import brep_cache

jacks = list(brep_cache.iter_instances(r"JACK CYL"))                 # 경로 정규식
weight = list(brep_cache.iter_instances(top_assembly="COUNTER WEIGHT:1"))  # 최상위 하위조립
shape = brep_cache.load_part(jacks[0].instance_path)                # 배치 적용(전역, mm)
local = brep_cache.load_part(jacks[0].prototype_entry, placed=False)  # 프로토타입 좌표
both = brep_cache.load_compound(jacks)                              # 여러 부품을 한 compound로
T = jacks[0].transform                                              # 4×4 numpy (전역 ← 프로토타입)
```

- `load_part(key, placed=True)`: `key`는 `instance_path` 또는 `prototype_entry`. 엔트리에 `placed=True`는 인스턴스가 1개일 때만 허용한다(여러 개면 `ValueError`).
- 읽을 파일은 `prototypes.csv`의 `prototype_file`이 정한다. `read_brep(path)`는 확장자로 형식을 고른다(`.bbrep` 바이너리, 그 밖은 ASCII). 그래서 ASCII 사본이나 다리·마스트의 옛 `.brep`도 같은 함수로 읽는다. 별도의 자동 폴백은 두지 않았다(목록과 파일이 어긋나면 `FileNotFoundError`와 manifest 경고로 드러나게).
- 프로토타입 파일은 처음 한 번만 읽고 메모리에 둔다. 돌려주는 핸들은 새 `TopoDS_Shape`라 `Move`해도 캐시가 바뀌지 않는다. `clear_memory_cache()`로 비운다.
- 첫 호출 때 `check_cache.warn_if_stale(["06_brep"])`로 STEP 크기·수정 시각과 캐시 파일 존재·크기를 확인하고, 다르면 `UserWarning` 하나(문제 5개까지 나열)를 낸다(해시 계산 없음, 0.1 s).

### 8.4 검증 (`verify_brep_cache.py`, 판정 통과)

캐시만 읽어 다시 계산한 값과 비교했다(STEP을 읽지 않음). 표본이 아니라 **1,214개 인스턴스 전부**를 비교했다. 바이너리로 바꾼 뒤 다시 실행했고(243 s) 결과는 ASCII 때와 같다.

| 항목 | 기준 | 결과 |
|---|---|---|
| 키 조인(`instance_path`, `prototype_entry`, `product_name`, `is_mirrored`) | 불일치 0 | 양쪽 1,214행, 불일치 0 |
| 부피(단위 밀도, 부피 > 10⁻³ mm³인 1,165개) | 상대차 ≤ 1×10⁻⁶ | 최대 1.9×10⁻¹³ |
| 부피 0 부품 49개(면도 없는 빈 형상, 16 프로토타입 — 9절에서 정정) | 절대차 | 0 mm³ |
| 무게중심(전역 좌표) | 절대차 ≤ 1×10⁻⁶ mm | 최대 2.6×10⁻¹¹ mm |
| 관성 텐서(단위 밀도, 무게중심 기준, 전역 축) | Frobenius 상대차 ≤ 1×10⁻⁶ | 최대 2.1×10⁻¹¹ |
| 인스턴스 bbox(`AddOptimal`) | 절대차 ≤ 1×10⁻⁶ mm | 최대 1.0×10⁻⁷ mm |
| 조립 전체 bbox | 절대차 ≤ 1×10⁻⁶ mm | 2.3×10⁻¹³ mm (X ±1536.5, Y −1050.9…10437.5, Z −3001.0…4033.2) |
| 기존 다리 B-rep `02_legs/legs/*.brep` 8개 | 위상 개수 같음, 꼭짓점 ≤ 1×10⁻⁹ mm | 8/8, 최대 4.5×10⁻¹³ mm |
| 기존 마스트 B-rep `04_mast/mast/*.brep` 743개 | 같음 | 743/743, 최대 9.1×10⁻¹³ mm |

다리(JACK CYL), 마스트(MAST), 오거(DRIVE AUGER ASSY·AUGER TOOL) 묶음별 통계도 `verification.json`의 `mass_properties_groups`에 있다(모두 위 최대값 이하).

**질의 속도:** STEP 직접 질의는 부품 하나를 보려 해도 전체 읽기·XCAF 변환이 필요하다(125 s, 정점 3.9 GB). 바이너리 캐시에서는 다리 부품 하나 0.085 s(색인 읽기 포함), 프로토타입 681개 전부 3.4 s, 그 뒤 1,214개 배치 compound 0.01 s다.

### 8.5 캐시 목록 (`01_cad/cache_manifest.json`, `check_cache.py`)

- 기록: STEP(이름·크기·수정 시각·sha256), 캐시 폴더 `00_step`~`09_sim_shapes`(10개: `00_step`·`01_parts`·`02_legs`·`03_auger`·`04_mast`·`05_meshes`·`06_brep`·`07_faces`·`08_style`·`09_sim_shapes`, 2026-10-21 `cache_manifest.json` `caches` 기준)마다 생성 스크립트(경로·sha256·git blob 해시·마지막 커밋, 지금은 커밋 전이라 null)와 파일 목록(경로·크기·sha256·생성 스크립트·git 제외 여부), 기록 시점의 Python·pythonocc-core 8.0.1.2·OCCT 8.0.1·numpy·trimesh·pandas 버전.
- `06_brep`의 생성 스크립트는 파일별로 기록된다: `build_brep_cache.py`(프로토타입·표), `convert_brep_cache.py`(`format_conversion.json`), `verify_brep_cache.py`(`verification.json`), `derive_crawler_cache.py`(`derived/crawler/*`).
- 점검 `check_cache.py`(기본, 0.1 s): STEP 크기·수정 시각 변경, 등록 파일 누락·크기 변경은 **오류**, 등록 안 된 새 파일과 생성 스크립트 변경은 **경고**. `--full`(약 2 s)은 STEP과 모든 파일의 sha256을 다시 계산한다. `--strict`는 오류가 있으면 종료 코드 1, 함수 `check(strict=True)`는 `StaleCacheError`를 낸다.
- 캐시를 다시 만들면 `check_cache.py --write [--cache 이름]`으로 목록을 갱신한다. `build_brep_cache.py`와 `convert_brep_cache.py`는 끝에서 `06_brep` 항목을 스스로 갱신한다. 다른 생성 스크립트(`derive_crawler_cache.py` 포함) 뒤에는 `--write`를 수동으로 실행한다.

### 8.6 크롤러 파생 캐시 (`01_cad/06_brep/derived/crawler/`, C5·C7·C8 준비)

크롤러 프로토타입 하나를 읽는 데 3 s, 면 156,614개를 모두 훑는 데 약 8분이 걸린다. 그래서 쓰임새별 결과를 한 번 뽑아 두었다(`derive_crawler_cache.py`, 2026-10-20 실행 463 s, 정점 3.4 GB). **이 크롤러는 STEP 설명상 다른 기종(REXOME25)의 하부체**라서, 값은 "CAD에 그려진 하부체"의 치수다. 모든 파일에 출처(원본 프로토타입 `0_1_1_746.bbrep`의 sha256 `d3142659…fbe6e`, 인스턴스 배치, 생성 스크립트 경로·sha256, 생성 시각)를 JSON `provenance`로 기록했다. 좌표는 CAD 전역(mm, Y-상방)이고 `*_body_m`은 기체 축(x = +Z_cad, y = +X_cad, z = +Y_cad, CAD 원점, m)이다.

| 파일 | 용도 | 내용 | 크기 | git |
|---|---|---|---|---|
| `crawler_summary.json` | C7 | 지면 높이, 트랙 중심 간격, 슈 접지 폭, 트랙 길이, 높이 띠별 접지 패치(±X 사각형), 슈 피치, 앞선 검토값 대조, 출처 | 5 kB | 추적 |
| `crawler_ground_faces.csv` | C7 | 최저점이 지면 +3 mm 안인 면 2,096개(종류·법선·bbox·면적·중심) | 0.33 MB | 추적 |
| `crawler_grouser_tips.csv` | C7 | 아래를 향한 수평 평면(지면 +120 mm 안): 그라우저 끝 높이 분포(트랙 길이 방향 형상) | 0.12 MB | 추적 |
| `crawler_wheels.csv` | C7 | 둥근 솔리드를 축별로 묶은 바퀴 위치(지름, 축 Y·Z, 폭, 역할 추정) | 3 kB | 추적 |
| `crawler_solids.csv` | C5·C8 | 솔리드 3,214개의 부피·무게중심·bbox·소속(left/right/center) | 0.42 MB | 추적 |
| `crawler_face_stats.json` | C5 | 높이 띠·면 종류·소속별 면 수, 색인 범위 권고 | 2 kB | 추적 |
| `crawler_collision.json` | C8 | 트랙별 B-rep 부피·bbox, 상자 근사, 볼록 껍질, 메시 부피 비교 | 6 kB | 추적 |
| `track_left_hull.obj`, `track_right_hull.obj` | C8 | 트랙별 볼록 껍질(2,248면, CAD mm) | 각 68 kB | 추적 |
| `crawler_lowres.obj` | C8 | 저해상도 시각 메시(CAD mm) | 20.8 MB | **제외**(`*_lowres.obj`). 재생성: `& C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts\00_cad\derive_crawler_cache.py` (프로젝트 루트, 약 8분, 다른 파생 파일도 함께 다시 쓴다) 뒤 `check_cache.py --write --cache 06_brep` |

**C7 값 (CAD 측정, 크롤러 바닥 Y −1,050.92 mm = 기체 z −1.0509 m)**

| 항목 | 이번 측정(B-rep 면) | 앞선 검토(`cad_origin_mass_imu.md` 2.6절) | 비교 |
|---|---|---|---|
| 트랙 중심 간격(반) | ±1,045.0 mm(좌우 대칭, ±0.001 mm) | 1.045 m | 일치 |
| 슈 접지 폭(그라우저 끝 X 범위) | 421.97 mm (X 834.0…1256.0) | 0.423 m | 1 mm 차 |
| 평탄 접지 길이 +1 mm | 1,636.7 mm (Z −825.1 … +811.6 = 기체 x −0.825 … +0.812 m), 그라우저 10개/측 | 1.64 m (x −0.826 … +0.813) | 일치 |
| 평탄 접지 길이 +3 mm | 1,636.7 mm (+1 mm와 같음) | 1.84 m | **다름**. 다음 그라우저 끝은 +3.8 mm(+Z 끝)·+4.4 mm(−Z 끝)에 있다. ~~앞선 값은 렌더 메시(선형 편차 3 mm)로 잰 것이라 메시 오차가 섞인 것으로 보인다(추정)~~ **정정(2026-10-21)**: 원인은 메시 오차가 아니라 **띠 정의**다. 첫 들린 끝 슈 패드가 기울어 가장 낮은 모서리는 +2.23 / +2.37 mm, 중심은 +4.39 / +3.81 mm에 있어, 모서리 정점을 넣은 이전 선택은 1,839.2 mm, 면 중심으로 나눈 이번 값은 1,636.7 mm가 된다([cad_crawler_ground.md](cad_crawler_ground.md) 3.1절) |
| 평탄 접지 길이 +5 mm / +10 mm | 1,994.3 mm (Z −1005.0…989.3) / 2,004.5 mm | — | +4.0 mm 높이에 폭 489 mm(X 800…1290)의 큰 수평면도 있다. ~~슈 판 하면으로 보임(추정)~~ **정정(2026-10-21)**: **접지 슈 블록의 바닥면**(489.2 × 88.1 mm/슈, 아래로 패드 4개가 4.0 mm 돌출)이다. 슈 판 하면은 +47.0 mm에 있다([cad_crawler_ground.md](cad_crawler_ground.md) 3.2절) |
| 슈 피치 | 173.2 mm (지면 그라우저 중심 간격, 173.2~173.3) | — | |
| 트랙 전체 길이(측면 솔리드 Z 범위) | 3,684.2 mm | bbox 3.68 m | 일치 |
| 하부 롤러 | 측마다 6개, Ø194 mm, 축 Y −790.7, Z −884 / −527 / −170 / +187 / +544 / +901 (간격 357 mm) | — | |
| 끝 바퀴 −Z(후방) | Ø548 mm, 축 Y −583.2, Z −1405.0 | — | 아이들러로 보임(추정) |
| 끝 바퀴 +Z(전방) | Ø525 mm(둥근 부분), 같은 축에 Ø658.8 mm 비원형 링(톱니로 보임), 축 Y −582.7, Z +1400.0 | — | 스프로킷으로 보임(추정, 이름이 아니라 형상으로 판단) |
| 끝 바퀴 축 간 거리 | 2,805 mm | — | |
| 상부 롤러(캐리어) | **측마다 1개**(2026-10-21 정정), 축 Z 0.0 · Y −332.72 (기체 x 0.000, z −0.3327 m), y ±1.045 m | 답면 Ø120×35 mm 2개 + 가운데 플랜지 Ø140, 링크 레일 하면이 답면에 닿음(간격 0.000 mm) | 롤러·축·받침대가 한 솔리드(234/1900)라 bbox 원형 조건으로는 빠졌다. 축 방향 원통면으로 찾음(`04_scripts/00_cad/check_upper_run.py`, `upper_run_check.json`·`.png`). 상부 런은 롤러 위 꼭짓점에서 만나는 직선 두 개(+2.23°/−1.87°, 처짐 없음). 롤러는 트랙 프레임 윗판(Y −380.1)의 구멍(Z ±75)에 들어앉아 브래킷이 받침판 22에 얹힌다. 프레임과 최소 거리 9.18 mm·간섭 없음, 상부 링크 레일과는 0.008 mm 접선 접촉(`01_cad/09_sim_shapes/upper_roller_overlap_check.png`). 이전 기록: 찾지 못함 |

**C8 형상 (트랙 한쪽, 좌우 같음)**

| 형상 | 면 수 | 부피 | 원본 B-rep 대비 | bbox 차 |
|---|---|---|---|---|
| B-rep(솔리드 1,548개) | — | 5.696×10⁸ mm³ | 기준 | — |
| 세밀 메시(편차 5 mm/0.5 rad) | 2,207,748 | −0.41 % | 부피 검증용 | 0.013 mm |
| 볼록 껍질 `track_left_hull.obj` | 2,248 | 3.68배 | 트랙 고리 안쪽까지 채움 | 0.013 mm |
| 상자 근사(`crawler_collision.json` `box`) | 6 | 4.19배 | 중심 기체 (0.0021, ±1.0283, −0.5709) m, 반치수 (1.842, 0.338, 0.480) m | 0 |
| 저해상도 메시 `crawler_lowres.obj` | 274,005 | −13.5 %(남긴 솔리드 기준 −9.0 %) | 부피 상위 95 % 솔리드 303개만 남기고 각각 2차 오차 감축(목표 −90 %). 얇은 판은 감축이 일찍 멈춰 면 수가 크다. **시각화 전용**(부피·질량에 쓰지 않음) | 5.4 mm |

- 가운데 부분(선회 링·센터 프레임, 솔리드 118개)은 저해상도 메시에서 부피가 −51 %로 크게 줄었다(큰 판이 감축으로 꺼짐). 시각화 품질이 중요하면 `05_meshes`의 렌더 메시를 쓰는 편이 낫다.
- 접지 충돌은 볼록 껍질이나 상자보다 `crawler_summary.json`의 접지 패치(+1 mm 사각형: X 834…1256, Z −825…812)가 실제 접지면에 가깝다. 구 배열(R13)을 고칠지는 dynamics-expert가 판단한다.

**C5 근거 (`crawler_face_stats.json`)**: 크롤러 면 156,614개는 조립 전체 면(인스턴스 포함 226,000개)의 69 %다. 최저점 기준 지면 +3 mm 안은 2,096개(1.3 %), +50 mm 안은 10,950개(7.0 %), +400 mm 안은 72,887개(46.5 %)다. 종류는 원통 53,140, 평면 36,141, B-스플라인 26,090, 원환 19,660, 구 11,044, 원뿔 10,539개다. 바퀴·링크·핀·프레임 면은 장착면이나 접지면 후보가 아니므로, C5 면 색인에서 크롤러는 **지면 +50 mm 안의 면과 아래를 향한 그라우저 끝 평면만** 넣는 것을 권고한다.

#### 8.6.1 크롤러 접촉 부품 B-rep과 색인 (D안, 2026-10-20)

크롤러 접촉 D안(CLAUDE.md "크롤러 접촉 배치", YAML `contact.crawler.sphere_layout`)의 접촉 위치마다 그 위치를 이루는 솔리드 묶음을 따로 저장하고 색인했다. 하부 롤러 6개/측, 틈 있는 끝 슈 3개/끝(6개/측), 참고로 평탄 접지 슈 10개/측이다. 양쪽 트랙을 합쳐 **44개 부품**이다. 입력은 캐시뿐이다(크롤러 프로토타입 `0_1_1_746.bbrep`, 8.6절 파생 표, 9절 면 색인, `parts_classified.csv`의 밀도, YAML은 대조용으로 읽기만 한다). STEP은 읽지 않는다. 다른 기종(REXOME25) 하부체의 **그려진 형상**이다.

```powershell
& C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts\00_cad\derive_crawler_parts.py   # 약 2분, 메모리 정점 1.1 GB
& C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts\00_cad\check_cache.py --write --cache 06_brep
```

**구조** (`01_cad/06_brep/derived/crawler/`)

| 파일 | 내용 | 크기 | git |
|---|---|---|---|
| `parts/<part_id>.bbrep` | 부품마다 솔리드 묶음 compound 1개. BinTools 바이너리, **CAD 전역 좌표(mm, Y-상방, 크롤러 배치 적용), 배치 = 항등**. 기체 좌표 변환은 색인 JSON `frames`에 있다 | 44개 84.6 MB(롤러 133 kB, 슈 2.6 MB씩) | **제외**(`.gitignore` `01_cad/06_brep/derived/crawler/parts/`) |
| `crawler_contact_parts.csv` | 부품 44행 색인(아래 열) | 37 kB | 추적 |
| `crawler_contact_parts.json` | 같은 행 + 출처(입력 sha256, 생성 스크립트 sha256, 시간·메모리), 좌표계, 밀도, 식별 규칙 정의, 슈 규칙 데이터, 검증 결과 | 122 kB | 추적 |
| `crawler_contact_part_solids.csv` | 부품 ↔ 솔리드 번호(`crawler_solids.csv` 키), 솔리드 부피, 첫 면 번호·면 수 | 40 kB | 추적 |
| `derive_parts.log` | 진행 로그 | — | 제외 |

**부품 ID와 순번.** `<kind>_<side><n>`. `kind` = `roller` / `end_shoe` / `flat_shoe`, `side` = `L`(왼쪽, +X_cad = 기체 +y) / `R`. `n` = `order_index` + 1이고 `order_index`는 기체 x 오름차순(뒤 → 앞) 0부터다. **롤러·끝 슈의 `order_index`는 YAML `roller_x_m`·`end_shoe_x_m`(·`end_shoe_gap_m`) 배열 인덱스와 같다**(`yaml_key`, `yaml_index` 열). 예: `end_shoe_L1` = `end_shoe_x_m[0]` = −1.3122 m(뒤 끝 가장 바깥), `end_shoe_L4` = `end_shoe_x_m[3]` = +0.9505 m(앞 끝 가장 안쪽). 평탄 슈는 `flat_shoe_L01`…`L10`.

**대상 식별 규칙**

- **롤러**: `crawler_wheels.csv`의 `track roller` 축마다, 축 둘레 상자 안에 **완전히 들어가는** 솔리드 = 바퀴(Ø194) 1, 축(Ø70×352) 1, 양 끝 브래킷 2, 장착 볼트 4, 와셔 4 = **12개**(역할은 형상으로 추정). 상자: CAD X 중심 ±200 mm, Z 축 ±100 mm, Y 바퀴 바닥 −1 mm ~ 바퀴 꼭대기 +1 mm. 위쪽 한계를 −500 mm까지 올려도 같은 12개라 프레임 판(Z 방향으로 길다)은 들어오지 않는다.
- **슈 단위(끝 슈·평탄 슈) 경계 정의**: 트랙 한 피치의 강체 묶음.
  1. 접지 슈 = 그라우저 패드 평면 4개(각 2,108.5 mm², `export_params.py`와 같은 기준)를 가진 솔리드(600×72×130 mm).
  2. 슈 판 = 접지 슈 바로 위의 같은 폭(600 mm) 솔리드 중 가장 큰 것(600×43×199 mm). 같은 부피의 솔리드가 측마다 44개(트랙 전체 피치 수)다.
  3. 체인 솔리드 후보 = 슈 판 중심에서 350 mm 안, bbox 대각선 700 mm 미만, 롤러 묶음 아님, 그리고 솔리드 순서에서 체인 블록 구간 안(접지 슈가 26개 주기로 반복되는 구간 ± 1주기). 후보마다 **3D 무게중심이 가장 가까운 슈 판**에 붙인다.
  4. 가운데 평탄 슈의 묶음(26개)을 템플릿으로 삼아, 템플릿 부피에 없는 후보를 빼고 다시 붙인다(측마다 1개 빠짐).
  - 결과: 슈 단위 = 접지 슈 1, 슈 판 1, 그 판에 볼트로 붙은 링크 쌍 2, 판 가장 가까운 트랙 조인트(핀 1, 부싱 1, 씰 원판 2), 슈 볼트 4·너트 4, 측면 블록 2와 그 체결구 8 = **26개**(역할 이름은 형상 추정). 남은 후보가 측마다 정확히 1,144개 = 44 × 26이고, 32개 슈 모두 같은 부피 구성이다. 묶음은 CAD 솔리드 번호로도 연속 구간 하나다(예: `end_shoe_L1` = 469…494).
  - 조인트는 이웃 두 슈 판까지의 거리가 트랙이 굽어도 변하지 않으므로(조인트가 두 판의 회전축 위에 있다) 직선부와 끝 바퀴 둘레에서 같은 규칙이 성립한다. 가장 가까운 판과 두 번째 판의 거리 차는 최소 16.1 mm다.
  - 끝 슈 대 평탄 슈: 그라우저 패드 최저점이 바닥 위 1×10⁻³ mm보다 높으면 끝 슈다(`export_params.py`와 같은 기준). 끝마다 3개다.

**색인 열** (`crawler_contact_parts.csv`, 71열)

| 열 | 뜻 |
|---|---|
| `part_id`, `kind`, `side`, `end`(끝 슈: rear/front), `order_index`, `yaml_key`, `yaml_index` | 식별·YAML 대응 |
| `solid_count`, `solids` | 솔리드 번호(`;` 구분, `crawler_solids.csv`의 `solid`) |
| `file`, `file_bytes`, `sha256` | B-rep 파일 |
| `density_g_cm3`, `volume_mm3`, `mass_kg`, `compound_volume_rel_diff` | 밀도 7.85(크롤러 XCAF 재질 없음 → `parts_classified.csv`의 부모 제품명 '강철', 질량 표와 같은 값). 부피·질량은 솔리드별 `VolumeProperties`를 `GProp_GProps.Add`로 합친 값. `compound_volume_rel_diff`는 compound 전체에 한 번 `VolumeProperties`를 건 값과의 상대차(최대 2.1×10⁻⁶, 원점에서 먼 B-스플라인 적분 차, 참고) |
| `com_{x,y,z}_cad_mm`, `com_{x,y,z}_body_m` | 무게중심 |
| `I{xx,yy,zz,xy,xz,yz}_body_kg_m2`, `I{1,2,3}_principal_kg_m2` | 관성(무게중심 기준, 기체 축, kg·m²), 주관성 모멘트 |
| `bbox_{min,max}_{x,y,z}_cad_mm`, `..._body_m` | bbox(`AddOptimal`) |
| `lowest_above_ground_mm` | 부품 전체 최저점 − 바닥(Y −1,050.92 mm) |
| `face_count`, `face_ranges`, `indexed_face_count` | 면 번호 구간(포함 끝, `TopExp_Explorer(프로토타입, FACE)` 순 = 9절 `face_index`). `indexed_face_count` = 그중 9절 면 색인에 행이 있는 면 수(크롤러는 지면 +50 mm 띠만 색인됨) |
| 롤러: `roller_wheel_solid`, `roller_axis_{x,y,z}_body_m`, `roller_axis_dir_body`, `roller_radius_mm`, `roller_width_mm`, `roller_bottom_above_ground_mm`, `roller_tread_face_indices` | 바퀴 솔리드의 가장 큰 볼록 원통 면(축 ∥ X_cad = 기체 y)에서 잰 축 위치·반지름·폭. 롤러 면은 지면 +163 mm 위라 9절 색인에 없으므로 B-rep 곡면에서 직접 계산했다 |
| 슈: `ground_shoe_solid`, `shoe_plate_solid`, `grouser_lowest_above_ground_mm`, `gap_m`, `ground_face_area_mm2`, `ground_normal_{x,y,z}_body`, `ground_tilt_deg`, `ground_face_indices` | 그라우저 패드 평면 4개: 최저점 높이(= **틈**, YAML `end_shoe_gap_m` 기준), 면적 합, 면적 가중 바깥 법선(XDir × YDir, REVERSED면 반전), 수직에서 기운 각, 면 번호 |
| `station_x_body_m`, `station_x_rounded`, `yaml_value`, `yaml_gap_m`, `gap_rounded_m` | 위치(롤러 = 트레드 원통 축, 슈 = 패드 평면 무게중심 Z_cad 평균)와 YAML 대조 |

**예시 행(왼쪽, 오른쪽 같음)**

| 부품 | 위치 x [m] | 틈 / 최저점 [mm] | 질량 [kg] | 기타 |
|---|---|---|---|---|
| `roller_L1` | −0.8840 | — / 163.2 | 52.84 | 축 (−0.884, 1.045, −0.7907) m, R 97.0 mm, 트레드(가장 큰 원통면) 폭 219.0 mm, 면 75679–75808 |
| `end_shoe_L1` (뒤 3번째) | −1.3122 | 21.49 / 21.49 | 57.56 | 패드 면적 8,434 mm², 법선 기체 (−0.0556, 0, −0.9985), 3.19° |
| `end_shoe_L3` (뒤 1번째) | −0.9663 | 2.23 / 2.23 | 57.56 | 같은 기울기 3.19° |
| `end_shoe_L4` (앞 1번째) | +0.9505 | 2.36 / 2.36 | 57.56 | 법선 (+0.0372, 0, −0.9993), 2.13° |
| `flat_shoe_L01` | −0.7863 | 0 / 0 | 57.56 | 법선 (0, 0, −1) |

- 끝 슈 3개의 패드 법선이 끝마다 같다(뒤 3.19°, 앞 2.13°). 끝 롤러에서 아이들러·스프로킷으로 올라가는 트랙이 직선 경사라서 틈이 피치마다 같은 양씩 는다(뒤 9.63 mm, 앞 6.45 mm/피치).
- 끝 슈의 부품 전체 최저점은 패드 최저점보다 최대 0.0015 mm 낮을 뿐이다. 틈은 패드 기준으로 써도 된다.
- 롤러 바닥은 지면 위 163.2 mm다. D안의 롤러 구(바닥 높이)는 롤러 → 링크 → 슈 → 바닥 하중 경로를 롤러 축 위치에 모은 **모델 가정**이다. 뒤·앞 끝 롤러(x −0.884 / +0.901 m)는 평탄 슈 범위(−0.786 … +0.773 m) 밖, 첫 들린 슈(틈 2.2 / 2.4 mm) 근처에 있다.

**로더** (`brep_cache.load_crawler_part`)

```python
import brep_cache
shoe = brep_cache.load_crawler_part("end_shoe", "L", 0)   # YAML end_shoe_x_m[0], CAD 전역 mm
roller = brep_cache.load_crawler_part("roller", "R", 5)   # YAML roller_x_m[5]
```

색인 CSV에서 행을 찾아 `read_brep`으로 읽는다(메모리 캐시 없음, 슈 1개 0.02 s).

**검증** (`crawler_contact_parts.json` `verification`, 판정 통과)

| 항목 | 기준 | 결과 |
|---|---|---|
| 롤러 x, 끝 슈 x ↔ YAML | 0.1 mm 반올림 같음 | 24행 불일치 0(반올림 전 최대 차 0.047 mm) |
| 끝 슈 틈 ↔ YAML `end_shoe_gap_m` | 0.01 mm 반올림 같음 | 12행 불일치 0(반올림 전 최대 차 0.0049 mm) |
| 롤러 축 \|y\| ↔ `track_centre_y_m` 1.045 | 0.1 mm 반올림 같음 | 차 0(반올림 전 0.0005 mm) |
| 개수 | 측마다 롤러 6·끝 슈 6(끝마다 3)·평탄 슈 10 | 같음 |
| 솔리드 집합 겹침 | 없음 | 976개 모두 다름 |
| 부피 = 해당 솔리드 부피 합 | 상대차 ≤ 1×10⁻⁹ | 다시 읽은 파일에서 최대 6.2×10⁻¹³ |
| 같은 구성 | 롤러 12개·슈 26개, 부피 구성 같음 | 44개 모두 같음 |
| 다시 읽은 B-rep 꼭짓점 | 차 0 | 0 mm |
| 좌우 대칭(X_cad 거울) | 부피 ≤ 1×10⁻⁵, 위치 ≤ 0.01 mm | 부피 2.9×10⁻⁷, 무게중심 ≤ 1.6×10⁻⁵ mm, 위치·최저점 ≤ 1×10⁻¹¹ mm. 오른쪽 솔리드 부피가 왼쪽과 수 mm³ 달라 부피 기준은 1×10⁻⁵로 두었다 |
| 면 번호 체계 | 9절 `solid_index` = 면 번호 구간의 솔리드 | 크롤러 11,290행 모두 일치. 슈마다 패드 면 4개가 색인에 있다(`selection` = `ground_band`) |

생성 2026-10-20: 크롤러 읽기 3 s, 부품 44개 쓰기·질량 특성 95 s, 검증 18 s, 합계 112 s, 메모리 정점 1.12 GB.

**상부 롤러(캐리어) 부품 (2026-10-21)**: `derive_crawler_upper_rollers.py`가 측마다 상부 롤러 1개를 같은 방식으로 저장·색인한다(`parts/upper_roller_{L,R}1.bbrep`, `crawler_upper_rollers.csv/.json`, `crawler_upper_roller_solids.csv`, 면 표 `01_cad/07_faces/crawler_upper_roller_faces.csv.gz`; 로더 `brep_cache.load_crawler_upper_roller(side)`, `face_index.load_crawler_upper_roller_faces()`). 부품은 롤러 솔리드(바퀴·축 보스·받침대가 한 솔리드, 좌 234/우 1900)와 받침대 볼트 4·와셔 4로 22.516 kg(STEP 밀도 7.85)이다. 프레임에 용접된 나사 받침판(좌 22)은 프레임에 남긴다. 축은 기체 (0.000, ±1.045, −0.3327) m(축 방향 y)이고, 답면은 Ø120 × 35 mm 2개(간격 84 mm), 플랜지는 Ø140 × 79.7 mm다. 회전부 질량 17.16 kg·축 둘레 관성 0.0368 kg·m²는 원통 절단 **추정**이다(축 포함, Ø80 보스 제외). 검증: 좌우 대칭 ≤ 6e-13, 재로드 부피 7e-13, `upper_run_check.json`과 일치, `check_cache.py --check` 0 오류. STEP 원본은 크롤러가 하위 제품 없는 shrinkwrap이라 읽지 않았다(더 얻을 정보 없음).

## 9. 전체 면 색인 (C5, 2026-10-20)

부착점·접촉면·구멍 축을 STEP이나 B-rep을 다시 열지 않고 표 질의로 찾으려고, 조립 전체의 면을 색인했다. **프로토타입마다 한 번**(681개) 면을 분석하고 `instances.csv`의 배치 행렬로 1,214개 인스턴스에 옮겼다. 입력은 B-rep 캐시(8절)뿐이고 STEP은 읽지 않는다.

### 9.1 구조 (`01_cad/07_faces/`)

| 파일 | 내용 | 크기 | git |
|---|---|---|---|
| `prototype_faces.csv.gz` | 프로토타입 면 58,747행, **프로토타입 좌표(mm)** | 1.7 MB | 제외 |
| `instance_faces.csv.gz` | 인스턴스 면 80,676행, **CAD 전역(mm, Y-상방) + 기체(m)** | 4.4 MB | 제외 |
| `face_index_summary.json` | 개수(종류·선택별), 크롤러 제외 개수, 시간·메모리, 출처(sha256), 프로토타입별 면적 합·위상 점검 | 0.24 MB | 추적 |
| `face_index_verification.json` | 9.4절 검증 결과, 질의 시간 | 4 kB | 추적 |
| `build.log` | 진행 로그 | — | 제외 |

재생성: `& C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts\00_cad\build_face_index.py`(프로젝트 루트, 약 2.5분 + 검증 2분, 메모리 정점 1.5 GB) 뒤 `check_cache.py --write --cache 07_faces`. 검증만 다시: `--verify-only`. 크롤러 전체 면 포함: `--crawler-all`.

**열** (인스턴스 표, `*_cad*` = CAD 전역, `*_body*` = 기체 축 x = +Z_cad, y = +X_cad, z = +Y_cad, 원점 = CAD 원점)

| 열 | 뜻 |
|---|---|
| `instance_path`, `prototype_entry`, `product_name`, `top_assembly`, `parent_assembly` | 키·부품명·최상위 조립·바로 위 조립(경로의 끝에서 두 번째) |
| `face_index` | `TopExp_Explorer(프로토타입, TopAbs_FACE)` 순번(0부터). 같은 캐시 파일이면 재현된다. 크롤러는 제외한 면이 있어도 원래 번호를 유지한다 |
| `solid_index`, `solid_valid` | 면이 처음 속한 솔리드의 순번(고유 솔리드 탐색 순), 솔리드 밖 면은 −1. `solid_valid` = 그 솔리드가 `BRepCheck_Analyzer` 통과 |
| `selection` | `all`(일반), 크롤러는 `ground_band`(지면 +50 mm 안) / `grouser_tip`(아래 향한 그라우저 끝 평면) |
| `kind`, `reversed` | `GeomAbs` 종류(plane·cylinder·cone·sphere·torus·bspline 등), 면 방향이 REVERSED인지 |
| `area_mm2` | 면적(mm²), `brepgprop.SurfaceProperties` |
| `centroid_{x,y,z}_cad_mm`, `centroid_{x,y,z}_body_m` | 면 무게중심(면적 중심) |
| `normal_{x,y,z}_cad`, `normal_{x,y,z}_body` | **평면만**: 바깥 법선 = 평면 XDir × YDir, REVERSED면 반전 |
| `axis_*`, `axis_point_*`, `radius_mm`, `radius2_mm`, `cone_half_angle_rad` | 원통·원뿔·구·원환: 축 방향(부호 임의), 축 위 점(면 중심을 축에 투영, 구는 중심), 반지름(원뿔은 기준 반지름, 원환은 큰 반지름), 원환 작은 반지름, 원뿔 반각(rad) |
| `convex` | 회전면의 바깥 법선이 축에서 멀어지는 쪽인가: True = 축·보스, False = 구멍·보어 |
| `bbox_{min,max}_{x,y,z}_cad_mm`, `..._body_m`, `bbox_recomputed` | 면 bbox(`AddOptimal`). 축 정렬 배치(856개 인스턴스)는 프로토타입 bbox를 옮긴 값(정확), 비정렬 배치(358개)는 배치한 면에서 다시 계산(24,674행) |
| `normal_uncertain` | 솔리드 밖 면(열린 셸) 또는 무효 솔리드의 면: 법선·내외부 판정을 믿을 수 없음 |

### 9.2 규모

- 인스턴스 면 80,676행 = 크롤러 밖 69,386 + 크롤러 11,290(`ground_band` 10,950 + `grouser_tip` 340). 크롤러 전체면 226,000행(8.6절 값과 같음)이다.
- 종류별(인스턴스 면): 평면 40,254, 원통 25,026, 원뿔 7,407, 원환 4,278, B-스플라인 2,985, 구 726.
- **크롤러 제외분**(`0:1:1:746`, 다른 기종 REXOME25 하부체): 156,614개 중 145,324개 제외(원통 48,534, 평면 32,457, B-스플라인 25,242, 원환 18,624, 구 10,568, 원뿔 9,899, 면적 합 1.333×10⁸ mm²). 개수는 `face_index_summary.json` `crawler`에 있다. 같은 크롤러 조립의 `SHELL`(`0:1:1:745`, 726면)은 별도 프로토타입이라 전부 넣었다.
- **부피 0 부품 49개(16 프로토타입)는 면이 없다**(솔리드·셸·면 0, 빈 형상). 8.4절의 "면만 있는 형상"이라는 설명은 틀렸다. 그래서 색인 행이 없다(`instances_without_faces` 49).
- `normal_uncertain` 4,622행: 솔리드 밖 면 744행(크롤러 조립의 `SHELL` 726, `COMPOUND` `0:1:1:30` 3면 × 6인스턴스) + 무효 솔리드 면 3,878행(`부마씨이 소구경 3D_Shrinkwrap_11` 2,414, `4. 1st GEAR` 1,258, `30-1. TOP COVER` 103 × 2).

### 9.3 질의 (`04_scripts/00_cad/face_index.py`)

```python
import sys
sys.path.insert(0, r"C:\workspace\outrigger_control\04_scripts\00_cad")
import face_index

# IMU C1 가로판 윗면: 위를 향한 평면, 기체 좌표 창(m)
c1 = face_index.query(kind="plane", normal_body=(0, 0, 1), tol_deg=1,
                      bbox=((0.24, 0.475, 0.035), (0.44, 1.215, 0.045)))
# 다리 패드 바닥: 아래를 향한 큰 평면
pads = face_index.query(kind="plane", normal_body=(0, 0, -1), tol_deg=1,
                        instance="JACK CYL", area_min_mm2=5e4)
# 오목 원통(구멍·보어): 축 기체 z, 반지름 범위
bores = face_index.query(kind="cylinder", convex=False, axis_body=(0, 0, 1),
                         radius_mm=(20, 80), top_assembly="FRONT JACK CYL:1")
```

- 조건: `kind`, `normal_body`(부호 있음)·`axis_body`(부호 무시)와 `tol_deg`, `convex`, `area_min_mm2`/`area_max_mm2`, `radius_mm`(값 또는 범위), `bbox`(기체 m) + `bbox_mode`(`overlap`/`inside`/`centroid`), `instance`·`product`·`top_assembly`(정규식), `include_uncertain`. 결과는 DataFrame 사본.
- `face_index.load()`(인스턴스 표, `prototypes=True`면 프로토타입 표)는 처음 한 번 읽고 메모리에 둔다. 첫 호출 때 `check_cache.warn_if_stale(["07_faces"])`.
- 속도: 새 프로세스에서 import + 읽기 0.9 s(읽기 0.4 s), 질의 한 번 3~15 ms.
- 예시 결과: C1 질의 → `BASE DECK:1` 면 2562 하나(면적 0.1426 m², z 0.040 m, bbox x 0.240~0.440·y 0.475~1.215 m). 패드 질의 → 다리 4개 바닥면, 면적 0.1071 m², z 전방 −0.6998·후방 −0.7120 m(`cad_summary.json` −699.8·−712.0 mm와 같음). 보어 질의 → `FRONT JACK CYL:1`의 수직 오목 원통 2개(R 55.0·57.5 mm).

### 9.4 검증 (`face_index_verification.json`, 판정 통과)

| 항목 | 기준 | 결과 |
|---|---|---|
| 프로토타입별 면적 합 vs `SurfaceProperties(프로토타입)` | 상대차 ≤ 1×10⁻⁹ | 681개 모두 0(같은 면 집합). 탐색 면 수 = 고유 면 수(중복 면 0) |
| 법선 자체 점검(UV 중심의 곡면 법선 + 방향) | 평면 법선·원통 `convex` 일치 | 49,274면, 실패 0 |
| 바깥 방향 점검(`BRepClass3d_SolidClassifier`, 면 위 점 ±0.05 mm) | 바깥 OUT·안 IN | 유효 솔리드의 평면·원통 3,000개 표본(고정 시드, 크롤러 제외) 중 면 위 점이 있는 2,836개: 통과 2,834, **반전 0**, 모호 2(양쪽 OUT 또는 양쪽 IN — 얇은 판·겹친 솔리드, 2 mm에서는 정상). 무효 솔리드(`Shrinkwrap_11`)에서는 반전 1건이 있었다 → `normal_uncertain`으로 표시 |
| `02_legs/leg_faces.csv` 대조(8 인스턴스) | 행 수·종류·면적·bbox | 384 = 384행, 종류 불일치 0, 면적 상대차 3.9×10⁻¹⁰, bbox 5.0×10⁻⁷ mm, 원통 축 0°, 반지름 2.8×10⁻¹⁴ mm |
| `04_mast/mast_faces.csv` 대조(696 인스턴스) | 같음 + 축 위치 | 49,675 = 49,675행, 종류·솔리드 번호 불일치 0, 면적 4.9×10⁻¹⁰, bbox 5.2×10⁻⁷ mm, 원통 축 6×10⁻⁴°, 축선 거리 6.7×10⁻⁷ mm, 반지름 4.8×10⁻⁸ mm |
| 기존 표 평면 법선 | 부호 무시 각도 | 최대 6×10⁻⁴°. **부호는 다리 40면·마스트 7,327면에서 반대**: 기존 표는 평면 축 방향(`Axis().Direction()`)을 그대로 적어 면 방향(REVERSED)을 반영하지 않았다. 바깥 방향이 필요하면 이 색인을 쓴다 |
| 중심 | 기존 표에 무게중심 없음 | bbox 중심 차 최대 6.2×10⁻⁷ mm, 평면 무게중심이 기존 bbox 밖인 면 0 |
| 크롤러 그라우저 끝(`crawler_grouser_tips.csv`) | 아래 향한 평면(지면 +120 mm 안) | 628 = 628개, 중심 거리 최대 7.5×10⁻⁷ mm, 면적 3.3×10⁻⁹, 높이 5.8×10⁻⁷ mm. 지면 높이 끝 평면 80개(기존 80) 모두 기체 z −1.050919 m = 지면, x −0.825~+0.812 m |
| IMU C1 가로판 윗면 | 질의로 찾음 | 1개, z 0.040 m(9.3절) |

생성 2026-10-20: 프로토타입 분석 130 s(솔리드 유효성 점검 46 s 포함, 크롤러 96 s), 인스턴스 변환 18 s, 쓰기 4 s, 합계 152 s, 메모리 정점 1.42 GB(검증 포함 1.52 GB). 검증 110 s.

### 9.5 C7·C8에 쓰기

- C7(크롤러 접지): `selection == "grouser_tip"`이거나 `ground_band`인 아래 향한 평면으로 접지 패치·슈 피치를 표 질의로 다시 뽑을 수 있다(파생 캐시와 같은 값).
- C8(충돌 형상): 패드 바닥·크롤러 접지면은 법선·bbox가 있어 상자·평면 접촉 정의에 바로 쓴다. 핀 구멍(`convex=False` 원통)의 축선(`axis_*`, `axis_point_*`)은 관절 축 후보다. 부품별 면 집합은 `instance_path`로 묶어 프리미티브 근사 범위를 정할 수 있다.
