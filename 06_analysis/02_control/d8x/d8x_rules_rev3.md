# D8x 검증 범위 확장 판정 규칙 — 덧붙임판 3 (rev3, K1 전환 태그판)

- 작성: control-expert, 2026-11-10. 봉인 sha는 같은 폴더 `d8x_rules_rev3.sha256`에 있다.
- 바탕 문서(모두 고치지 않는다)
  - 원판 `d8x_rules.md`: sha256 `a377b9bb028385bb7d7d97312a71816ba0ca758e2cb193e25b2d092fff064da8`, 커밋 28d5aab
  - rev1 `d8x_rules_rev1.md`: sha256 `ad16f452fb4dce7395a059c73d7caf213f1a9a69f18af8d230bf03f4518e80d4`, 커밋 9e2b9e2
  - rev2 `d8x_rules_rev2.md`: sha256 `5f3fa620fe704834a9b6c0a65824b29b75e2a527ea8e97a17abb5e07987a8c27`, 커밋 f1e8ac5
- 계기: K1(LAS-b R4c30 순서 관문, `SlopeClearanceMarginSettings.flat_soil_margin_order_gate`) 채택 전환이 master에 병합됐다(`b53d890`, 구현 `b0979d1`). R8 프리셋 `C2Config.with_10hz_d1()`의 관문 기본값이 **켬**이 됐고, 태그가 V0 `final_C4G2_LAS_K1`, VB `final_C4G2_P3_LAS_K1`이 됐다. 클래스 기본값(`C2Config()`)은 꺼짐 그대로다.
- 이 판이 대체하거나 추가한 절만 바뀐다. 나머지는 원판·rev1·rev2 그대로다.
- **판정 항목 J1~J11, 문턱, 관문 순서(G0 → G1 → …), 기대 수, 점 좌표, 비대칭 마름모 경계(roll 5.7° / 앞내림 3.7° / 앞들림 3.6°), G0-4 범위(rev2 3)와 W 자격(참 $R_v$ ≤ 1.01, rev2 3), d45 W 후보 문턱 1.01(rev1 4.3), 불변·승계(7절), 두 경로 재집계, 판정 등급은 바꾸지 않는다.**
- 규약·기호·$F_{D8}$ = 14,414.589 N은 원판과 같다. 이 판의 K1은 LAS-b K1이다. touch-phase K1(2026-11-05 탈락)과도, 하네스 키 토큰 `K1`(크롤러 강성 ×1)과도 다르다.

## 공개: 봉인 시점에 본 것과 없는 것

| 구분 | 내용 |
|---|---|
| 본 것: G0 rev1 | 커밋 `e37f42c`(2026-11-10 02:56:20, 브랜치 `worktree-agent-a237987a3ad0eb520`, master·`d8x-impl` 미병합)의 `06_analysis/00_dynamics/d8x_g0_rev1.json`: 60/60 통과(재사용 33 + 재계산 27). 커밋 메시지의 최소 여유(G0-1 상단 `d45-+` +0.34 mm, G0-2 `roll-` +52.5 kN, G0-3 4.30°, G0-4 관문 상단 `pitch+` $\hat R_v$ 1.00492, `fup3.6` G0-1 +7.67 mm, W 후보 11점 모두 자격)과 JSON `meta.reuse_condition`(17개 import 파일 + YAML blob id) |
| 본 것: K1 | REM 판정서 `las_k1_rem_judgement.md`(`4c509d15…6780`, 등급 `통과`), 전환 후 감사 원문 `las_k1_switch_post_audit.md`(`2c02dc9e…94e7`, 차단 0) |
| 본 것: 코드 | `d8x-impl`(35df06c)의 `d8x_record.py`·`d8x_judge.py`·`d8x_spec.py`·`acc_d8.py`·`d1_runs.py` 해당 부분, master `v5_options.py` 태그 함수, 경로 2 `d8x_recount.py`(sha256 `46010967729e190ab572775db9dd59b083a3856558c3f07a239bf601bed9d9d1`) |
| 없는 것 | **R-a·R-c·Chrono D8x 결과는 0건이다.** 새 점의 폐루프 결과를 하나도 보지 않았다 |

rev2 봉인(03:10:48) 때는 G0 rev1 결과를 보지 않았다(rev2 "공개"). 이 판은 그 결과를 본 뒤에 쓴다. 다만 이 판은 G0 결과를 근거로 쓰지 않고, G0를 **다시 계산하도록** 정한다(4절). 그래서 본 G0 값이 판정에 들어가지 않는다.

## 0. 원판·rev1·rev2와의 관계

| 원판·rev1·rev2 절 | rev3 처리 |
|---|---|
| 원판 2.1 둘째 항목(봉인 시점 태그, "K1은 끔"), rev2 4 첫 문단의 기대 태그 | **대체**(1절) |
| 원판 2.1 첫째 항목("`with_10hz_d1()`를 덮어쓰지 않음") | **K1에 한한 예외 추가**(2절) |
| 원판 6 E-6, rev2 4(`final_C4G2` 금지, LAS-b 켬) | **대체**(3절) |
| 원판 8 경로 2 사용법 | **보충**(3.3절) |
| rev1 3 G0 재사용 | **대체**(4절, 재사용 조건 불성립 → 60평가 전체 재계산) |
| rev1 9.2-4 `judge-g0`·`select-w` 입력, rev2 7 | **보충**(5절 구현 위치) |
| 그 밖 | 그대로 |

## 1. 태그 (원판 2.1 둘째 항목, rev2 4 기대 태그 대체)

| 묶음 | 팔 | 관문 | 기대 태그(`expected_tag`) |
|---|---|---|---|
| R-a td_main·td_robust·td_kt(910) | K1 끔 | **명시적 끔**(False 설치) | `final_C4G2_LAS` |
| R-a-K1(192) | K1 켬 | 명시적 켬(True 설치, 프리셋과 같음) | **`final_C4G2_LAS_K1`** |
| R-c VB(96) / V0(96), ε {0, 2e-3} | K1 끔 | **명시적 끔**(False 설치) | VB `final_C4G2_P3_LAS` / V0 `final_C4G2_LAS` |
| R-c-K1 VB(48) / V0(48), ε 0 | K1 켬 | 명시적 켬(True 설치) | **VB `final_C4G2_P3_LAS_K1` / V0 `final_C4G2_LAS_K1`** |
| Chrono C(19, V0) | K1 켬 | 프리셋 그대로(설치 없음) | **`final_C4G2_LAS_K1`** |
| G0(60) | 해당 없음(정적 계산, 제어기 없음) | — | — |

- K1은 Chrono 시작 전에 채택됐다. 그래서 원판 7절 V-1b 마지막 문장대로 **Chrono는 채택 태그로 바로 돌고, V-1은 기록이 된다.** V-1·V-1b의 짝 비교(K1 끔 팔 ↔ K1 켬 팔 `commands_sha256`)와 `K1_DEPENDENT` 표시·원판 10절 FLAG (iii)·B-V는 그대로다.
- G1의 판정 대상(K1 짝 제외 R-a 910, R-c 192)과 "K1 짝 행도 J1~J11은 판정함"(원판 5.0)은 바꾸지 않는다. 그 결과 전환 뒤 채택 제어기와 같은 구성의 하네스 행은 K1 켬 팔(R-a-K1 192, R-c-K1 96)뿐이다. 이는 원판 구조 그대로이며, 두 팔의 차이는 V-1이 짝 해시로 판정한다.
- VB는 R-c 하네스에만 있다. Chrono 19행은 V0 하나다(원판 Q6).
- 실제 값은 실행 전 기록에 적는다: Chrono는 I-5 `d8x_prelaunch_C.json`의 `expected_tag`, 하네스는 묶음별 실행 전 기록(`d8x_judge.py prelaunch`)의 `expected_tags`(묶음 × 팔 × 설정). 위 표와 다르면 실행하지 않는다.

## 2. K1 끔 팔의 명시적 끔 (원판 2.1 첫째 항목의 K1 예외)

- 원판 2.1 "`with_10hz_d1()`를 덮어쓰지 않음"은 **K1 한 키만 예외**로 한다. 이유: 원판의 K1 끔 팔은 봉인 시점 프리셋(관문 꺼짐)을 뜻했다. 전환 뒤에는 "설치 없음"이 켬이 되므로, 끔 팔이 원판과 같은 제어기가 되려면 관문을 명시적으로 False로 둬야 한다. 그 밖의 설정(LAS-b 포함)은 덮어쓰지 않는다(rev2 4).
- 하네스 행은 두 팔 모두 **K1 요청을 명시**한다(`off` / `on`). 요청이 없거나(None) 알 수 없는 값이면 그 행을 실행하지 않는다(실행 전 크게 실패). "끔 = 아무것도 설치하지 않음"은 쓰지 않는다.
- 한 프로세스에 다른 값을 두 번 설치하면 크게 실패해야 한다(같은 값 두 번은 멱등).
- 기록(행마다): K1 요청(`off`/`on`)과 **실제 제어기 설정에서 읽은 값**(`k1_order_gate` = `effective_k1(controller)` = `controller.config.slope_clearance_margin.flat_soil_margin_order_gate`). 태그는 실제 제어기 설정으로 만든다(`v5_options.controller_tag(options, controller.config)` / `with_switch_tags`). 설치 전 설정이나 요청에서 태그를 만들지 않는다.
- Chrono 행 기록: d8x 블록의 `controller_tag`, `k1_order_gate`(실제 제어기 값), `liftoff_slow_enabled`, 그리고 result.json `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate`.

## 3. E-6 (원판 6 E-6, rev2 4 대체)

### 3.1 행 조건 (하나라도 거짓이면 그 행은 판정 불가)

| # | 조건 | 하네스 | Chrono |
|---|---|---|---|
| E-6a | 행 태그 = 1절 표의 그 행 묶음·팔·설정 `expected_tag`(문자열 완전 일치) | 참이어야 | 참이어야 |
| E-6b | LAS-b 태그: `outrigger_sim.hydraulics.v5_options.is_liftoff_slow_tag(tag)`가 참. **`tag.endswith("_LAS")`로 판단하지 않는다**(`_LAS_K1`에서 거짓이 됨) | 참 | 참 |
| E-6c | K1 태그: `v5_options.is_order_gate_tag(tag)` = (팔 == 켬) | 같아야 | 참이어야 |
| E-6d | 실제 관문 기록 `k1_order_gate` is (팔 == 켬). 요청 기록 = 팔 | 같아야 | 참이어야. 그리고 `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate` 참 |
| E-6e | LAS-b 기록 `liftoff_slow_enabled` is True | 참 | 참 |
| E-6f | 태그가 LAS-b 꺼짐 태그(`final_C4G2`, `final_C4G2_P3`, `final_C4G2_K1`, `final_C4G2_P3_K1`)가 아님. E-6b의 결과와 같아야 한다(중복 검사) | 참 | 참 |

- 태그 필터로 행을 고를 때 필터 전후 수를 출력하고 필터 뒤 수 = 기대 수인지 확인하는 원판 E-6 둘째 문장은 그대로다. 필터는 1절 표의 완전 일치 태그로 하고, 접미사(`_LAS`, `_K1`) 문자열 비교로 하지 않는다.

### 3.2 묶음 조건

- 한 묶음 파일 안의 태그 히스토그램은 그 묶음·팔에 해당하는 1절 태그만 가져야 한다(R-c는 설정 2종). 다른 태그가 하나라도 있으면 그 묶음의 E-1 수 비교 전에 문제로 보고한다.

### 3.3 경로 2 `d8x_recount.py`가 새 태그를 받는 방법 (원판 8 보충)

- 경로 2는 결과 전에 고정했다: sha256 `46010967729e190ab572775db9dd59b083a3856558c3f07a239bf601bed9d9d1`, 사본 `C:\workspace\outrigger_control\.local_archive\session_9d4aec18_20261110\d8x_path2\d8x_recount.py`(시험 `test_d8x_recount.py` `906f899c…74e8ec`). **고치지 않는다.**
- 코드 읽기로 확인한 동작
  - 기본 기대 태그 `DEFAULT_EXPECT`는 봉인 시점 태그다: `ra` off/on 모두 `final_C4G2_LAS`, `rc` VB off/on `final_C4G2_P3_LAS`, V0 off/on `final_C4G2_LAS`, `chrono` `final_C4G2_LAS`. 그대로 돌리면 K1 켬 팔과 Chrono 행이 모두 `E-6 tag … != expected` 판정 불가가 된다(크게 실패, 조용하지 않음).
  - 태그 비교는 `--expect` 값과의 완전 일치 + `FORBIDDEN_TAGS = ("final_C4G2", "final_C4G2_P3")`다. `endswith("_LAS")`를 쓰지 않으므로 `_LAS_K1`을 받는 데 코드 변경이 필요 없다. LAS-b는 `liftoff_slow_enabled is True` 기록으로 본다.
  - 하네스 K1은 `k1_order_gate is (k1 == "on")`로 본다(R-a `run["k1_order_gate"]`, R-c `d1.d8x.k1_order_gate`, `job.k1` = 파일 역할). Chrono 행은 태그·LAS-b만 보고 `k1_order_gate`는 보지 않는다. Chrono의 실제 관문 점검(E-6d)은 경로 1과 태그(실제 제어기 설정으로 만든 `_K1`)로만 한다. 이 비대칭을 판정서에 적는다.
  - `_load_expect`는 최상위 키(`ra`, `rc`, `chrono`)를 **통째로** 바꾼다(하위 키 병합 없음). 그래서 `rc`를 주면 VB·V0 × off·on 넷을 모두 줘야 한다.
- **판정 실행은 반드시 `--expect <파일>`을 준다.** 파일 내용은 1절 표와 같아야 한다:

```json
{"ra": {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS_K1"},
 "rc": {"VB": {"off": "final_C4G2_P3_LAS", "on": "final_C4G2_P3_LAS_K1"},
        "V0": {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS_K1"}},
 "chrono": "final_C4G2_LAS_K1"}
```

- 이 파일(권장 `06_analysis/02_control/d8x/d8x_expect_k1.json`)은 실행 전 기록(I-5, 하네스 prelaunch)과 같은 값으로 결과 전에 만들고 sha256을 판정서에 적는다. 경로 2 리포트의 `expect.source`가 그 경로인지 확인한다.
- G0는 4절대로 전체 재계산이므로 경로 2는 `--g0 <d8x_g0_rev3.json>`으로 판정하고 **`--g0-base`를 주지 않는다**(주면 `_g0_reuse_check`의 차이가 판정 불가 문제로 들어간다). 재사용 대조는 기록용 별도 실행으로만 한다(4절).

## 4. G0 전체 재계산 (rev1 3 대체)

- rev1 3의 재사용 조건은 "G0 실행 경로 파일의 git blob id가 3da8daa와 같음"이다. **이 조건은 깨졌다.**
  - `03_src/outrigger_sim/control/target.py`: G0 rev1(`e37f42c`)의 재사용 기록 blob `a786935242eb1da35a095251e8adb7ab5db895e2`. `d8x-impl`(35df06c)의 blob은 `f4d490e86c2cc349f896a78145925e747952aac5`(rev1 1.3 `VERIFICATION_EXT` 비대칭 구현)다. 이 파일은 `meta.reuse_condition.files`의 import 닫힘 안에 있다.
  - 함께: G0 단계 코드(3da8daa의 `run_s6_slope_boundary_check.py` `d8x_g0` 단계, `e37f42c`의 `run_d8x_g0_rev1.py`)는 master·`d8x-impl` 어디에도 병합돼 있지 않다.
- 처리: **G0 60평가(rev1 1.2 점 20 × 3단계)를 모두 다시 계산한다.** 재사용 0, 재계산 60.
  - 실행 위치: Chrono가 돌 커밋과 같은 G0 경로 blob을 갖는 커밋. 곧 K1 전환(`b53d890`)을 포함하고 `d8x-impl`의 `target.py`를 포함하며 G0 단계 코드를 병합한 구현 HEAD($H_{impl}$) 또는 $M$이다. 실행 시작·끝 `git status --porcelain --untracked-files=no` 빈 목록, 닫힘 파일 blob id를 기록한다(원판 I-1).
  - $H_{impl}$에서 돌렸다면 $M$에서 같은 닫힘의 blob id를 다시 비교한다. 하나라도 다르면 $M$에서 60평가를 다시 계산하고 그 결과로 판정한다(rev1 3의 "다르면 60평가를 모두 다시 계산" 원칙을 $M$에 적용).
  - 출력: 새 파일 `06_analysis/00_dynamics/d8x_g0_rev3.json`(`meta.rules_rev` "rev3", rev3 sha, `reuse` 0, `recompute` 60). `d8x_g0.json`(3da8daa)·`d8x_g0_rev1.json`(e37f42c)은 덮어쓰지 않는다.
  - 기준: G0-1~G0-3 60평가 전부, G0-4 관문은 rev2 3 범위(상단 L1-R `fdown3.7`·`fup3.6`·`roll5.7`·`rpX`), W 자격은 rev2 3(참 $R_v$ ≤ 1.01). 바뀐 것 없음.
  - 기록(등급 아님): rev3 60평가와 rev1 60평가(e37f42c)의 항목별 차(`G0_COMPARE_KEYS`: `s_max_m`, `F_static_min_N`, `swivel_deg`, `floor_hat_deg`). 차가 0이 아니면 값과 위치를 판정서에 적는다.
- `select-w`(rev1 9.2-4)의 입력은 `d8x_g0_rev3.json` 하나다(재사용 33 + 재실행 27 조합이 아님).
- 관문 G0(rev1 5.0)의 "rev1 3의 60평가(재사용 33 + 재실행 27)"는 "rev3 4의 60평가(재계산 60)"로 읽는다. 통과·실패 처리는 rev1 5.0 그대로다.

## 5. 구현 대상 위치 (python-expert가 `d8x-impl`을 새 master에 맞출 때. 원판 9.2, rev1 9.2, rev2 7에 추가)

이 판은 위치와 요구만 적는다. 코드는 python-expert가 쓴다.

| 위치(`d8x-impl` 35df06c 기준) | 요구 |
|---|---|
| `04_scripts/03_control/d8x/d8x_record.py` `install_k1_order_gate` | 값 인자(True/False)를 받아 그 값을 설치한다(2절). 같은 프로세스에서 다른 값 두 번 설치는 오류, 같은 값은 멱등. 지금은 켬만 설치하고 끔은 "설치 없음"이라 전환 뒤 끔 팔이 켬이 된다 |
| `04_scripts/03_control/touch_phase/acceptance/acc_d8.py` 191행 | `D8X_K1_ENV`가 `off`면 False 설치, `on`이면 True 설치, 그 밖(없음 포함)이면 D8x 실행 거부. `--k1` 기본값 없음(명시 필수) |
| `04_scripts/04_hydraulic/coupled/d1_runs.py` 491행 | D8x H-R-X 작업에서 `k1 == "off"`면 False 설치, `"on"`이면 True 설치, None이면 거부 |
| `04_scripts/03_control/d8x/d8x_spec.py` `DEFAULT_TAGS`(117행) | 1절 표대로 묶음 × 팔 × 설정 기대 태그(`ra` off/on, `VB` off/on, `V0` off/on, `chrono`) |
| `04_scripts/02_chrono/s6_stage2.py` `D8X_EXPECTED_TAG`(114행) | `final_C4G2_LAS_K1`(v5_options `LAS_K1_CONTROLLER_TAG`를 쓴다) |
| `04_scripts/03_control/d8x/d8x_judge.py` `_tag_problems`(197~208행, 202행) | E-6a~f(3.1절). LAS-b 판단은 `v5_options.is_liftoff_slow_tag`, K1 판단은 `is_order_gate_tag` + `k1_order_gate` 기록. R-c(632행)는 팔별 기대 태그를 쓴다(지금은 팔과 관계없이 `DEFAULT_TAGS[setting]`). Chrono는 `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate`도 본다 |
| `04_scripts/03_control/d8x/d8x_spec.py` `LAS_TAG_SUFFIX`(99행) | 태그 판단에 쓰지 않는다(삭제하거나 사용처 0) |
| `d8x_judge.py` `judge-g0`·`select-w`(추가) | rev3 4: 재사용 0 / 재계산 60 입력(`d8x_g0_rev3.json`)을 받는다. 재사용 blob 검사 대신 실행 커밋 닫힘 blob 기록을 확인한다 |
| 시험(추가) | (i) 전환 뒤 프리셋에서 끔 팔 → `k1_order_gate` False, 태그 `final_C4G2_LAS`/`_P3_LAS`, (ii) 켬 팔 → True, `_LAS_K1`/`_P3_LAS_K1`, (iii) 요청 없음 → 거부, (iv) `_tag_problems`가 `_LAS_K1`을 LAS-b 태그로 받음, (v) Chrono 기대 태그 = `final_C4G2_LAS_K1` |

- cad-expert(Chrono 행): d8x 블록에 `k1_order_gate`(실제 제어기 값)를 더 기록한다(2절). 그 밖은 rev2 7 그대로다.
- dynamics-expert: 4절 G0 60평가 재계산, 출력 `d8x_g0_rev3.json`.
- control-expert: 경로 2는 고치지 않고 3.3절 `--expect` 파일과 `--g0-base` 없는 G0 판정으로 쓴다.

## 6. 가정·위험 (추가)

- 하네스 V-1 짝(K1 끔 ↔ 켬)은 강체 지면이라 토양 LOC가 없어 R4·관문이 작동하지 않을 것으로 예상한다(감사 R-3 [추정]과 같은 근거, `c2.py` R4 조건 "soil mode used"). 예상일 뿐이며 V-1이 짝 해시로 판정한다.
- G0는 정적 계산이라 `target.py` 변경이 G0 값을 바꾸지 않을 것으로 예상한다. 예상일 뿐이며 4절 재계산이 판정한다. 차가 나면 4절 기록에 적는다.
- 경로 2는 Chrono 행의 실제 관문 값을 보지 않는다(3.3절). 경로 1만 E-6d를 직접 본다.
