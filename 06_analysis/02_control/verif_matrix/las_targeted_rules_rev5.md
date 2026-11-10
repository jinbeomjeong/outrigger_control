# LAS-b 표적·채택 규칙 덧붙임 판 5 (T-3을 K1 채택 제어기로: 관문 켬 실행, R-0 고정 + R-0K 기준선)

작성: control-expert, 2026-11-10.

> **상태: 봉인(2026-11-10).** SHA-256과 봉인 시각은 같은 폴더 `las_targeted_rules_rev5.sha256`에 있다(이 파일과 R-0K 키 목록 `las_targeted_rules_rev5_r0k_keys.json`, 두 줄). 이 파일은 더 고치지 않는다.
> - **고치는 판**: 판 4c `las_targeted_rules_rev4c.md`(`7e45993f667382f56aeb1b72bb5e7023ecfe3048a3723ac050cefc3b2a721417`)와 그 앞 판 전부. 앞 판은 원판(`00b48fd8…af40`), rev1(`0d5f59f8…7625`), rev2(`6be736cb…7960`), rev3(`956f65c7…91cd1`, 키 목록 `3602438d…8553`), rev4(`05fbde22…de6d`), rev4a(`3cbbfb5d…3b15`), rev4b(`add921e4…a6f3f`)다. 여기 적지 않은 항목은 그대로다.
> - 왜 고치나: LAS-b K1(R4c30 평탄 시작 순서 관문, 명세 437)이 2026-11-10에 R8 프리셋 기본 켬으로 전환됐다. rev3의 T-3 실행 조건·태그·기준선은 전환 전 프리셋(LAS-b b0, 관문 꺼짐)을 전제로 쓰였다. 사용자 결정(2026-11-10)은 "판정 묶음은 새 `_K1` 태그로 재실행, 봉인 판정 도구를 새 태그에 쓰려면 개정판"이다.
> - 이 판의 선택(사용자 결정 2026-11-10, 설계 메모 `las_t3_k1_design_note.md` 2절): Q1 (a) 관문 켬 `_LAS_K1`, Q2 (a) R-0 고정 + R-0K 45키, Q3 (a) 균일 연약 지면 키에서 `would_block`이 나오면 멈추고 묻는다, Q4 이름 `rev5`.

## 0. 본 것(결과 전 공개)

- **T-3 본 실행 결과는 0줄이다.** 저장된 것은 도구 연기 R-0 1행(decision_log 591, 12f9837 worktree, 저장 해시와 비트 같음)뿐이다. 관문 켬 조건의 T-3 줄, R-0K 줄은 하나도 없다.
- 이 판을 쓰려고 본 것은 아래뿐이다.

| 본 것 | 무엇을 봤나 |
|---|---|
| `las_targeted_rules_rev3_keys.json`(`3602438d…`) | 묶음별 키 구성(T-3a H-S-0 216 + H-S-1 12, T-3c H-S-A 72 + H-S-A-J2 4, T-3b dg3 G1 2키 × off/v4_on) |
| `v5/d1.jsonl`(`9039b36a…`, 저장 기준, LAS-b 끔·관문 꺼짐) | 키마다 `event_names["INFO_LOC_FLAT_SOIL_MARGIN"]` 개수, `commands_sha256`, `controller_tag`, `d1.verdict`, `wall_s` |
| dg3 저장 결과 JSON 4기록 | R4c30 흔적이 없음(사건 목록은 T4h 메타에 있어 실행 전에 다시 본다, 2.5) |
| `las_k1_rules.md` 부록 A 41~45행 | S-C(b0) 위 Y-Pa에서 해시가 바뀐 5키와 그 S-C 저장 해시 |
| 명세 437, `las_k1_judgement.md` K-4 | 관문의 동작, "`would_block_any` 거짓 줄 = 관문 꺼짐 해시" 규칙 |

- 계산은 읽기 전용 스크립트뿐이다. R-0K 키 목록은 `scripts/make_las_rev5_r0k_keys.py`(sha256 `54e6eff29b7b393dacfabf8774a5b609aa2ac849160d1c7d0ecbc60e457dbe24`)가 위 두 입력의 sha256을 확인한 뒤 만들었다.

## 1. 바뀌는 항목

| # | 앞 판 | 앞 문구 | 이 판 |
|---|---|---|---|
| 1 | rev3 2.1 실행 목록 | R-0 7 + T-3 308 | R-0 7 + **R-0K 45**(2.3) + T-3 308(**T-3K**로 부른다). 실행 순서 R-0 → R-0K → T-3K |
| 2 | rev3 2.2 실행 조건, H-T3-0 | 03_src 프리셋 = LAS-b b0, 래퍼 없음 | 묶음별 조건 표(2.2). T-3K는 프리셋 그대로(LAS-b b0 + 관문 켬, 래퍼 없음). 프리셋에 관문이 꺼져 있으면 H-T3-0 |
| 3 | rev3 3절 K-2·K-3 태그 | R-0 태그에 `_LAS` 없음, T-3 태그 `final_C4G2_LAS` / `final_C4G2_P3_LAS` | 2.2 표의 기대 태그. `_LAS`만 있고 `_K1`이 없는 T-3K 태그는 H-T3-3 |
| 4 | rev3 K-5·K-6 기준값 | 키 목록 값(= `d1.jsonl`, dg3는 저장 T4h 해시) | 기준선 $B(k)$(3.1) |
| 5 | rev3 K-0, 봉인 9개 | 원판·rev1~rev4·rev4a~c·rev3 키 목록 | **11개**: 앞 9개 + 이 판 + R-0K 키 목록 |
| 6 | rev4a 4 #2 dg3 설정 비교 | LAS-b 블록과 full-config 기록만 뺀다 | 정확한 키 `slope_clearance_margin.flat_soil_margin_order_gate` 하나를 더 빼고, 그 값은 묶음 조건과 따로 대조한다(2.5) |
| 7 | rev3 4절 멈춤 | H-T3-0~H-T3-6 | **H-T3-1K**, **H-T3-1Q**를 더한다(4절) |
| 8 | rev3 K-7 | 작동 줄 표 | 관문 열을 더한다(3.4) |

그대로인 것: rev3 K-1의 T-3 키 집합·수, K-4 문구(G1 균일 72 + T-3b 4, 작동 0이고 해시 = 저장 기준), K-6a~e의 문턱(사용자 채택 기준), H-T3-2(오류 줄 한 번 재시도), rev4·rev4a~c의 J-형식·`G6-2_loc`·None 실패 규칙, FB 끔.

## 2. 실행 조건

### 2.1 규약

- C2는 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, 음되먹임이다. 명령 $u$는 다리 행정 속도 [m/s](+ = 신장)다. 판정은 명령 해시(`commands_sha256`)와 `d1` 판정 블록으로 한다.
- **관문**은 `slope_clearance_margin.flat_soil_margin_order_gate`다(명세 437, LAS-b K1). 하네스 키 안의 `K1`(크롤러 강성 ×1)과 다르다.
- `would_block`은 관문이 R4c30을 막은 결정이고, `controller_meta.slope_clearance_margin.order_gate.decisions[*].would_block`에서 읽는다. `would_block_any`는 그 줄의 결정 가운데 하나라도 참인지다.
- R4c30 적용 여부는 `event_names["INFO_LOC_FLAT_SOIL_MARGIN"]` 개수로 본다. `events` 목록은 INFO가 잘려 있어서 쓰지 않는다.

### 2.2 묶음별 조건과 기대 태그

| 묶음 | LAS-b | 관문 | 프리셋 패치 허용(메서드 → 모듈) | 기대 태그 V0 / VB | dg3 off / v4_on |
|---|---|---|---|---|---|
| R-0 | 끔 | 끔 | `with_10hz_d1` → `pre_las_preset_runner`만 | 없음 / `final_C4G2_P3` | 없음 / `final_C4G2_P3`(rev3 그대로) |
| R-0K | 끔 | 켬 | `with_10hz_d1` → `las_t3_presets`만(LAS-b 기본값만 False로 바꾸고 관문은 프리셋 값) | `final_C4G2_K1` / `final_C4G2_P3_K1` | dg3 없음 |
| T-3K | b0 | 켬 | 없음 | `final_C4G2_LAS_K1` / `final_C4G2_P3_LAS_K1` | `final_C4G2_LAS_K1` / `final_C4G2_P3_LAS_K1` |

- 줄마다 제어기 설정을 대조한다: LAS-b 상태(b0 값 포함), 관문 값, `slope_clearance_margin.enable` True, `flat_soil_margin_m` 0.03. 어긋나면 그 줄은 오류 줄이다(H-T3-2 재시도 뒤에도 남으면 H-T3-3).
- `_FB`가 붙은 태그와 FB가 켜진 설정은 rev3대로 H-T3-3·H-T3-0이다.
- 스레드 변수, 워커, affinity, 정체성 기록은 rev3 K-0대로 한다. 세 파일(R-0, R-0K, T-3K)의 헤더 정체성은 서로 같아야 한다.

### 2.3 R-0K 키 목록

- 파일: `las_targeted_rules_rev5_r0k_keys.json`(이 판과 함께 봉인).
- 선택 규칙: rev3 키 목록의 T-3a·T-3c·R-0 D-1 키 가운데 `d1.jsonl` 줄의 `event_names["INFO_LOC_FLAT_SOIL_MARGIN"]` > 0인 키, 여기에 R-0 D-1 5키를 합친다.
- 결과: **45키**. 정렬한 키마다 LF를 붙여 UTF-8로 이은 목록의 sha256은 `9399c4922828973fe5129c6c5964dc2cf6c53137a8858d1f92e69f9c85452e3c`다. 묶음 소속은 R-0 5, T-3a 39, T-3c 6이다(한 키가 둘에 속할 수 있다).

| 분류(`class`) | 수 | 뜻 |
|---|---|---|
| `uniform_r4` | 36 | H-S-0 J1·J2, H-S-1 S1 균일 연약 지면. 저장 줄에 R4c30이 있다 |
| `patch_r4` | 5 | H-S-A-J2 `G1+J2@FL` T flat 4키 + H-S-A `G1+J1@FL` B flat V0 ε0.002. 저장 줄에 R4c30이 있다 |
| `r0_no_r4` | 4 | R-0 D-1 키 가운데 저장 줄에 R4c30이 없는 키(G1 T flat V0 ε0, J1 T diag-rec VB ε0, J2 M fup-rec V0 ε0.002, 경계 키 `H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0`) |

- dg3는 R-0K에 넣지 않는다. G1 균일이고 저장 기록에 R4c30이 없기 때문이다(2.5에서 확인).

### 2.4 전제 G(관문의 동일성)

관문은 R4c30 적용 여부만 바꾼다(명세 437.1). 그래서 같은 키의 관문 켬 실행과 꺼짐 실행은 첫 `would_block` 결정 전까지 비트 단위로 같다. 그 첫 결정은 꺼짐 실행에서 R4c30을 적용한 LOC다. 따라서 다음이 성립한다.

- (G-a) 저장 줄에 R4c30이 없는 키는 LAS-b 끔 + 관문 켬 실행이 저장 해시와 같고, `would_block_any`가 거짓이다.
- (G-b) 어떤 줄이든 `would_block_any`가 거짓이면 그 줄은 관문 꺼짐 실행과 해시가 같다.
- (G-c) rev3 K-5의 전제(LAS-b가 작동하지 않으면 명령은 LAS-b 끔과 비트 단위로 같다)는 관문 켬에서도 그대로다. 그러므로 R-0K 밖 키의 미작동 T-3K 줄은 저장 해시와 같고 `would_block_any`가 거짓이다.

이 전제가 깨지면 구현 결함으로 본다(4절 H-T3-1K, H-T3-5).

### 2.5 dg3(rev4a 4 #2 대체)

- 설정 비교에서 빼는 것은 rev4a의 LAS-b 블록과 full-config 기록, 그리고 정확한 키 `slope_clearance_margin.flat_soil_margin_order_gate` 하나다. 접두 `slope_clearance_margin` 전체를 빼지 않는다(R4c30 설정 `slope_clearance_margin.enable`·`flat_soil_margin_m`은 계속 비교한다).
- 뺀 관문 키의 값은 따로 대조한다: R-0 False, T-3K True. `las_t3_dg3.py`는 시작할 때 관문 상태를 출력하고, 프리셋 값이 묶음 조건과 다르면 실행하지 않는다.
- 실행 전(H-T3-0): dg3 4기록의 저장 T4h 메타 `events`에서 `INFO_LOC_FLAT_SOIL_MARGIN` 개수가 0인지 본다. 0이 아니면 H-T3-0이다(이 판에는 R-0K dg3 설계가 없다).

### 2.6 출력

새 폴더 `06_analysis/03_hydraulic/coupled/v5/las/t3_k1/`에 쓴다. 파일은 `las_T3_R0.jsonl`, `las_T3_R0K.jsonl`, `las_T3.jsonl`, `las_T3.md`, `las_T3_judge.json`, `t3_dg3_t4h/`다. rev3대로 이어쓰기와 덮어쓰기는 하지 않는다. 기존 `v5/las/`의 연기 산출물과 섞지 않는다.

## 3. 판정

### 3.1 기준선 $B(k)$

| 키 | $B(k)$ |
|---|---|
| R-0K 45키 | 그 키의 R-0K 줄(`commands_sha256`과 `d1` 판정 블록 전체: verdict, `fail_items`, items의 P3-2·`G6-2_loc`, FAULT 이름, `t_ready_s`, `stroke_max_m`) |
| 그 밖 D-1 키 | rev3대로 키 목록 값(= `d1.jsonl`. rev4a 1의 `key-list` 대조 그대로) |
| dg3 4기록 | rev3대로 키 목록의 저장 T4h 해시 |

- R-0K 줄의 `d1` 블록은 `d1.jsonl`과 같은 형식이다. G6-2는 `G6-2_loc`로 읽는다(rev4a 1).
- K-4(G1 균일 72 + T-3b 4)의 기준은 그대로 저장 해시다. G1 키는 R-0K에 없으므로 $B(k)$가 저장 기준과 같다.

### 3.2 K-2K(R-0K)

| # | 기준 | 실패하면 |
|---|---|---|
| K-1K | 키 집합 = R-0K 키 목록 45, 오류 줄이 남지 않음(H-T3-2 재시도 뒤) | H-T3-3 / H-T3-2 |
| K-2K (i) | 태그 = 2.2 표, LAS-b 끔, 관문 켬, 작동 0 | H-T3-3 |
| K-2K (ii) | `would_block_any`가 거짓인 줄은 `commands_sha256` = 저장 해시((G-b)) | H-T3-1K |
| K-2K (iii) | `r0_no_r4` 4키는 `would_block_any` 거짓이고 해시 = 저장 해시((G-a)) | H-T3-1K |
| K-2K (iv) | `uniform_r4` 36키는 `would_block_any` 거짓 | H-T3-1Q(멈추고 묻는다, 사용자 결정 Q3) |

- `patch_r4` 5키의 `would_block`은 기준이 아니다. 기록만 한다(3.5 예측).
- R-0 K-2(rev3)가 통과해야 R-0K를 시작하고, K-2K가 모두 통과해야 T-3K를 시작한다.

### 3.3 K-5·K-6(T-3K)

- **K-5**: 작동하지 않은 T-3K 줄은 `commands_sha256` = $B(k)$여야 한다. 추가로, R-0K 밖 키의 미작동 D-1 줄은 `would_block_any`가 거짓이어야 한다((G-c)). 어느 쪽이든 실패하면 H-T3-5다.
- **K-6**: 작동한 T-3K D-1 줄을 $B(k)$와 비교한다. K-6a~e의 정의와 문턱은 rev3·rev4a 그대로다. 작동 줄에서 관문이 막은 결정은 LAS-b가 LOC 시각을 옮겨 생긴 결과이므로 LAS-b 효과로 판정한다(LAS-b 단일 변수 짝).
- K-3: T-3K 태그와 설정은 2.2 표대로다.

### 3.4 K-7 기록 열 추가

작동 줄 표에 다음 열을 더한다: `would_block_any`, `applied`(R4c30 적용 결정 수), 첫 결정의 $dP = n_P - n_S$ [주기], 그 키의 기준선 출처(R-0K/저장), 기준선 줄과 결정 집합(`would_block` 참인 LOC)이 다른지. 기록이고 판정 기준이 아니다.

### 3.5 사전 예측(기준 아님)

| 예측 | 근거 | 확신 |
|---|---|---|
| R-0K `patch_r4` 5키는 `would_block_any` 참 | Y-Pa(S-C b0 + 관문)에서 해시가 바뀐 5키와 같다(`las_k1_rules.md` 부록 A 41~45, dP −4~−8주기) | 2키(`H-S-A-J2…V0\|e0`, `H-S-A…B…V0\|e0.002`)는 S-C b0 해시 = `d1.jsonl` 해시라 LAS-b 미작동 줄이었고, LAS-b 끔에서도 dP가 같다고 본다. 나머지 3키는 S-C 해시와 저장 해시가 달라 근거가 약하다 |
| R-0K `uniform_r4` 36키는 `would_block_any` 거짓 | S-C 진짜 연약 지면 R4 행 dP ≥ +31주기, REM R1~R6 dP +99~+206 | 높음 |
| T-3K G1 균일 76줄(K-4)은 관문과 무관 | 토양 모드가 서지 않아 R4c30 결정이 없다 | 높음 |
| 비용: R-0K 약 2.0 CPU·h(저장 `wall_s` 합 7,323 s), 전체 약 15.1 CPU·h | `d1.jsonl` `wall_s` | 추정 |

## 4. 멈춤(더하는 것)

| # | 조건 | 처리 |
|---|---|---|
| H-T3-1K | K-2K (ii)·(iii) 실패(전제 G 위반) | 멈춘다. 구현 결함으로 보고 python-expert 진단 뒤 다시 시험한다. T-3K는 시작하지 않는다. 종료 코드 1 |
| H-T3-1Q | K-2K (iv) 실패(균일 연약 지면 키에서 관문이 막음) | **멈추고 사용자에게 묻는다.** 그 키의 결정(dP, LOC 시각), 저장 줄과의 차이를 첨부한다. K1 채택 근거("균일 연약 지면에서 K1은 동작을 바꾸지 않는다", REM)와 어긋나므로 T-3보다 먼저 본다. 종료 코드 2 |

- 멈춤 순서: H-T3-0 → H-T3-3 → H-T3-2 → H-T3-1 → **H-T3-1K → H-T3-1Q** → H-T3-4 → H-T3-5 → H-T3-6.
- 종료 코드는 rev3대로다(0 통과, 1 기준 실패, 2 판정 없는 멈춤).

## 5. 사전 위험(결과 보기 전 기록)

- 437.5 F2(첫 R4 LOC를 막으면 끝까지 R4c30이 없음)가 T-3K 작동 줄에서 생길 수 있다. 이때 K-6e(행정 증가 ≤ 1 mm)는 통과 쪽이지만, P3-5(끝 크롤러 틈 ≥ 25 mm)가 거짓이 될 수 있다. 그 경우는 K-6b로 잡힌다.
- `patch_r4` 키의 R-0K 줄은 관문이 막아 저장 줄과 판정 블록이 달라질 수 있다(틈 목표 −30 mm). 이것은 관문 효과이고 T-3의 판정 대상이 아니다. 기준선으로만 쓴다.
- T-3K 작동 줄 가운데 R-0K 밖 키(저장 R4c30 없음)에서 LAS-b가 LOC 순서를 바꿔 R4c30이 새로 due가 되면, 관문이 그것을 막을 수 있다(경계 키 P5r4 현상의 b0판). 이것은 K-6 대상이다.

## 6. 다음 절차

python-expert 구현(설계 메모 4절, 이 판에 맞춘 차이는 판정서 작성 때 기록) → 단위 시험 → verif-protocol-auditor `[시점] 실행 전` 감사(차단 0) → compute-scheduler-expert 배치표 → 사용자 실행 승인.
