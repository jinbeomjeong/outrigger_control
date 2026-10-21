# C11 STEP 색·레이어 정보

작성 2026-10-21 (cad-expert). 원본 `REXOME33_Assy_r3(미니어쳐).stp`(630,777,519 B, Autodesk Inventor 2020, AP214)는 읽기만 했다.

## 1. 결론

- **레이어 없음**: `PRESENTATION_LAYER_ASSIGNMENT` 0개다. XCAF(레이어 모드 켬)로 읽어도 레이어 0개였다. 그래서 `layer` 열은 비어 있다.
- **색은 세 수준에 있다**:

| 수준 | 엔티티 | 개수 |
|---|---|---|
| 솔리드 | `STYLED_ITEM` → `MANIFOLD_SOLID_BREP`/`BREP_WITH_VOIDS` | 4,664 / 4,668 (미지정 4개 = 곡면 모델 `SHELL_BASED_SURFACE_MODEL` 'Srf1', GROUP '복합1'(`\X2\BCF5D569\X0\1`)) |
| 면 | `STYLED_ITEM` → `ADVANCED_FACE` | 63,625 / 204,071 |
| 조립 인스턴스(외관 재정의) | `CONTEXT_DEPENDENT_OVER_RIDING_STYLED_ITEM`(CDORSI) | 184 (문맥 깊이 1: 16, 2: 135, 3: 33) |
| 기타 | `STYLED_ITEM` → `POLYLINE` 2, `MAPPED_ITEM` 1(NULL_STYLE, 모든 CDORSI가 덮어쓰는 대상) | |

- 색 엔티티 수: `COLOUR_RGB` 151개(서로 다른 RGB 60개), `PRESENTATION_STYLE_ASSIGNMENT` 152개, `SURFACE_STYLE_USAGE`·`FILL_AREA_STYLE_COLOUR` 각 151개, `SURFACE_STYLE_TRANSPARENT` 149개(투명도는 0, 0.34, 0.6 세 값), `MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION` 1개. `DRAUGHTING_PRE_DEFINED_COLOUR`, `CURVE_STYLE`, `INVISIBILITY`는 없다. 개수는 `grep -a`로 엔티티 머리를 센 값이고 스크립트 집계와 같다(`01_cad/08_style/style_summary.json`의 `entity_counts`).
- Inventor는 대부분의 색을 **조립 수준의 외관 재정의(CDORSI)** 로 썼다. 인스턴스 1,214개 중 1,176개(97 %)가 재정의를 받는다. 1,005개는 상위 하위조립에서, 171개는 자기 위치에서 받는다. 나머지 37개는 부품 자체 색이고, 1개(크롤러 곡면 셸)는 색이 없다. 재정의 색이 부품 자체 색과 같은 경우는 40개뿐이다.

## 2. 표시색(재정의 적용) 대표값

| rgb_hex | STEP 값 (r, g, b) | 인스턴스 수 | 주요 부위 |
|---|---|---|---|
| `#ff4d06` | 1, 0.30196, 0.02353 | 721 | 구동부(DRIVE AUGER ASSY), 사이드 하우징·커버, 카운터웨이트 일부 |
| `#696969` | 0.41176 ×3 | 320 | 마스트, 탑시브, 하부 가이드, 데크·붐 |
| `#e0dfdb` | 0.87843, 0.87451, 0.85882 | 150 | 잭·붐·백스테이 실린더, 캐빈 일부 |
| `#bfbfbf` | 0.74902 ×3 | 7 | 오거 공구, 크롤러(재정의 없음, 부품 색) |
| `#3087e3`, `#013ef1`(투명 0.34) 등 | | 소수 | 캐빈 유리·표식(BUMA CE 3D) |

색 값은 STEP `COLOUR_RGB` 그대로다(0~1 표시값, sRGB). OCCT `Quantity_Color`로 비교할 때는 `Quantity_TOC_sRGB`로 꺼낸 값이 일치했고, 선형 값(`Quantity_TOC_RGB`)은 일치하지 않았다.

## 3. 방법

- `04_scripts/00_cad/build_style_index.py`는 STEP DATA 절을 텍스트로 한 번 훑는다(CAD 커널 없음, 약 12~56 s, 최대 메모리 0.33 GB, P코어 1개 고정). 표현 엔티티와 구조 엔티티(솔리드·셸·면, 표현·관계, PRODUCT 계통, NAUO, CDSR)만 파싱한다.
  - 경로 1: 스타일 → `PSA → SURFACE_STYLE_USAGE → SURFACE_SIDE_STYLE → SURFACE_STYLE_FILL_AREA → FILL_AREA_STYLE → FILL_AREA_STYLE_COLOUR → COLOUR_RGB`, 투명도는 `SURFACE_STYLE_RENDERING_WITH_PROPERTIES`에서 읽는다.
  - 경로 2: 대상 → 표현 → 제품 정의 → 제품.
  - CDORSI의 style context(변환 붙은 `SHAPE_REPRESENTATION_RELATIONSHIP`)는 CDSR을 거쳐 NAUO 사슬(루트부터)로 바꾼다. 사슬 연속성, 루트 시작, item이 마지막 인스턴스의 표현인지를 184개 모두 점검했다(문제 0건).
- 색 결정 규칙:
  - 표시색 `rgb_hex`: 인스턴스 경로의 가장 깊은 CDORSI(자기 또는 상위 조립)를 쓴다. 없으면 부품 대표색이다.
  - 부품 대표색 `part_rgb_hex`: 면마다 면 색, 없으면 솔리드 색을 정하고 면 수 기준 최빈값을 쓴다.
  - Inventor의 조립 외관 재정의가 부품의 면 외관까지 덮는다고 보았다. 이는 Inventor 동작 기준의 **해석**이다.
- 키 맞춤: 텍스트에서 만든 인스턴스 경로(루트 제품 이름 + NAUO 이름)를 `06_brep/instances.csv`의 `instance_path`와 1:1로 맞췄다. XCAF가 섞인 제품(솔리드 + 곡면 모델 + 와이어프레임)을 이름 없는 하위 성분 `=>[0:1:1:N]`으로 나눈 18행은 부모 제품의 표현 그룹 가운데 면 수가 같은 것과 짝지었다. 대상은 `0:1:1:30/31`(BYHT375-E-W_BD_3), `0:1:1:44/45`(부품8), `0:1:1:745/746`(크롤러)이다. prototype ↔ STEP 제품 정의는 모호한 경우 없이 1:1이다.

## 4. 검증

| 항목 | 결과 |
|---|---|
| 면 순서: STEP 면 순서(솔리드별·셸별·면 목록 순) ↔ `TopExp_Explorer(prototype, FACE)` 순서 | 07_faces `prototype_faces.csv.gz` 58,747행의 면 종류가 모두 같다. XCAF로 읽은 면별 실효 색(면 → 솔리드 → 부품)도 681개 prototype 모두에서 순서까지 같다(`xcaf_check.json`). 따라서 `face_styles.csv.gz`의 `face_index`는 C5 면 색인 번호와 같다. |
| 솔리드·면 색 RGB | XCAF(sRGB)와 완전히 같다(681/681). 색 테이블도 60개로 같다. |
| 레이어 | 텍스트 0개, XCAF 0개 |
| 인스턴스 재정의(CDORSI) 읽기 | 184개 중 **171개를 OCCT가 읽었다**. 13개는 읽지 않았다(4.1절). |
| 인스턴스 1,214개 표시색 | OCCT 실효색이 우리 display 색과 같은 인스턴스 214개, 부품 자체 색과 같은 인스턴스 1,000개, 그 밖 0개다(4.1절). |

XCAF 읽기(`--xcaf-check`, 색·레이어 모드 켬)는 단독 실행에서 119 s, 최대 메모리 3.98 GB였다(P코어 1개 고정, 2026-10-21 2차 실행). S4와 겹친 1차 실행은 465 s였다.

### 4.1 인스턴스 재정의 교차 확인 (OCCT 8.0.1, 2026-10-21 2차)

방법: 결과는 `xcaf_check.json`의 `instance_overrides`와 `instance_display_colour`에 있다.
- 문서 안의 SHUO는 모든 컴포넌트 라벨에 `XCAFDoc_ShapeTool.GetAllComponentSHUO`를 불러 셌다.
- 경로별 실효 스타일은 `XCAFPrs::CollectStyleSettings(root)`로 얻었다. 그 키를 위치가 적용된 면 → 솔리드 → 인스턴스 → 상위 조립 순으로 찾고, 가장 구체적인 키를 썼다(`XCAFPrs_AISObject`가 스타일을 나누는 방식과 같다).
- 인스턴스 대표색은 면 수 기준 최빈값이다.
- 큰 파일을 읽기 전에, 작은 중첩 조립 STEP으로 API 호출을 먼저 점검했다.

| CDORSI 대상 | 개수(깊이 1/2/3) | OCCT 8.0.1 동작 |
|---|---|---|
| 리프 인스턴스 | 171 (6/132/33) | 모두 읽었다. 위치가 적용된 인스턴스 키에 같은 색이 있다. 깊이 2·3은 SHUO로 저장된다(문서의 SHUO 165개 = 깊이 2·3 리프 재정의 132 + 33). 깊이 1은 컴포넌트 색으로 저장된다. |
| 하위조립 인스턴스(예: `LOWER GUIDE_ASSY:1`, `SIDE HOUSING_(ENGINE)_R1:1`, `ENGINE_COVER_3:1`) | 13 (10/3/0) | **읽지 않았다.** 컴포넌트 라벨 색, SHUO, 실효 스타일 키가 모두 없다. 읽지 않은 13개는 모두 하위조립 대상이다. |

인스턴스 표시색 분류(우리 `colour_source` 기준):

| 우리 출처 | 개수 | OCCT 실효색 = display | OCCT 실효색 = 부품 색 | 원인 분류 |
|---|---|---|---|---|
| assembly_override | 1,005 | 15 | 990 | **OCCT가 하위조립 대상 CDORSI를 읽지 않는다.** 15개는 재정의 색과 부품 색이 우연히 같다(같은 15개를 확인함). |
| instance_override | 171 | 161 | 10 | **적용 규칙 차이.** OCCT는 더 구체적인 솔리드·면 스타일을 인스턴스 스타일보다 우선한다. 우리 규칙은 재정의가 모두 덮는다. 다중 솔리드이거나 면 색이 있는 재정의 인스턴스 후보는 11개다(BASE DECK, BOOM, MAST BK, LOGO 등). 10개가 그 안에 든다는 것은 개수로 추정한 것이고, 행별로 대조하지는 않았다. |
| part | 37 | 37 | — | 일치 |
| none | 1 | 1 | — | 일치(둘 다 색 없음) |

결론:
- 우리 display 색은 STEP 원문(CDORSI)과 Inventor 동작 기준의 해석이다.
- OCCT 8.0.1 기반 뷰어·변환기(XCAF → glTF 등)는 인스턴스 1,000개를 부품 색으로 보여 준다. 이것은 OCCT 쪽의 한계·규칙 차이이고, 우리 색 표의 오류가 아니다.
- 그림에는 display(왼쪽)를 쓰고, OCCT 결과와 맞춰야 할 때는 `mode="part"`를 쓴다.

알려진 한계: 검사기의 SHUO 경로 이름 재구성이 경로와 맞지 않아, `examples[].shuo` 열은 비어 있다. 이 판정은 실효 스타일 키와 SHUO 개수로 했다.

## 5. 산출물 (`01_cad/08_style/`, manifest `08_style` 등록, `check_cache.py --check` 0 오류)

| 파일 | 내용 |
|---|---|
| `instance_styles.csv` | 인스턴스 1,214행. `instance_path`, `prototype_entry`, `rgb_hex`, `r g b`, `transparency`, `colour_source`(instance_override / assembly_override / part / none), `override_path`, `override_step_id`, `part_rgb_hex`, `part_face_share`, `part_colour_count`, `layer`(빈 값) |
| `prototype_styles.csv` | prototype 681행. 솔리드·면 색 개수, 대표색, `solid_colours`·`face_colours`(hex:개수) |
| `face_styles.csv.gz` | 면 204,071행. `face_index`(= 07_faces 번호), STEP 면 id, 종류, 실효 색, source(face/solid/none) |
| `palette.csv` | 서로 다른 RGB 60개와 수준별 사용 수 |
| `style_summary.json` | 엔티티 개수, 수준, 그룹, 키 맞춤, 분할 성분, 시간 |
| `xcaf_check.json` | XCAF 교차 확인 |
| `style_iso.png` | 앞-우-위 등각도. 왼쪽은 표시색, 오른쪽은 부품 자체 색 |
| `style_iso_rear.png` | 뒤-좌-위 등각도, 표시색 |
| `render_style_views.json` | 렌더 메타(시점 벡터, 색 개수) |

## 6. 질의 API (`04_scripts/00_cad/style_index.py`)

```python
import style_index
style_index.instance_colour(path)                 # 표시색 "#ff4d06" (기본)
style_index.instance_colour(path, mode="part")    # 부품 자체 색
style_index.colours_for(paths, default="#a8a7a0") # parts_classified.csv 행 순서 그대로
style_index.face_colours("0:1:1:2")               # {face_index: "#..."} (재정의 미적용)
style_index.prototype_style(entry), style_index.palette(), style_index.transparency(path)
```

S4 종합 그림·GIF에서는 `render_auger_descent.load_render_meshes`와 같은 행 순서로 `colours_for(table["instance_path"])`를 넘겨 `SceneItem` 색으로 쓰면 된다. 렌더 메시는 인스턴스당 색 1개만 지원한다. 그래서 여러 색이 섞인 35개 인스턴스는 대표색으로 칠하고 투명도는 그리지 않는다.

## 7. 한계·가정

- CDORSI가 솔리드·면 색까지 덮는다는 규칙은 Inventor 동작에 근거한 해석이다. OCCT 8.0.1과의 차이(하위조립 대상을 읽지 않음, 솔리드·면 스타일 우선)는 4.1절에 적었다.
- 크롤러(REXOME25 모델)는 재정의가 없어 부품 색 `#bfbfbf`이고, 곡면 셸 `0:1:1:745`는 색이 없다.
- 재생성: `python -I 04_scripts/00_cad/build_style_index.py [--xcaf-check]` → `python -I 04_scripts/00_cad/render_style_views.py` → `python -I 04_scripts/00_cad/check_cache.py --write --cache 08_style`
