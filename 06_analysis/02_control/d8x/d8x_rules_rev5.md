# D8x 검증 범위 확장 판정 규칙 — 덧붙임판 5 (rev5, 공개 정정·손 적용 순서판)

- 작성: control-expert, 2026-11-10. 봉인 sha는 같은 폴더 `d8x_rules_rev5.sha256`에 있다.
- 바탕 문서(모두 고치지 않는다)
  - 원판 `d8x_rules.md` `a377b9bb028385bb7d7d97312a71816ba0ca758e2cb193e25b2d092fff064da8`(28d5aab)
  - rev1 `ad16f452fb4dce7395a059c73d7caf213f1a9a69f18af8d230bf03f4518e80d4`(9e2b9e2)
  - rev2 `5f3fa620fe704834a9b6c0a65824b29b75e2a527ea8e97a17abb5e07987a8c27`(f1e8ac5)
  - rev3 `2318fb5cf75b64b525c515566776ed1ec6cbb10743621edc04c092d6774c7301`(589ff43)
  - rev4 `5233c517e6c0d17b0e26e902673e0d6990532ed1c54c82ae0801e688d50702a5`(f708bee)
- 계기: verif-protocol-auditor rev4 봉인 점검 원문 `06_analysis/02_control/d8x/d8x_rev4_seal_audit.md`(main checkout, 이 판을 쓸 때 git 미커밋, 끝에 메인 세션 덧붙임 절 포함, sha256 `986add3ada881f1818160d76b6f16fd8ef51d87d5b804502dc07416ced3a69b8`). 차단 0, 실행 전 수정 A-1~A-4.
- 사용자 결정(2026-11-10, 위 원문 "메인 세션 덧붙임")
  - A-1: 탐침 3건을 rev5에 공개한다.
  - A-2: **(b) V-2도 K1 켬 팔을 센다**(판정서 손 적용, 경로 1은 고쳐도 됨).
  - A-3: 손 적용 순서·결측 처리 문구는 control-expert가 정한다.
  - A-6: "$H_{impl}$는 메인 세션이 지정하고 실행 전 감사가 확인한다".
- **바뀐 판정은 A-2(2절) 하나와, rev4 1.4 손 적용의 적용 순서 명확화(3절)뿐이다.** 그 밖의 기준(J1~J11, 문턱, 관문 순서, 기대 수, 점 좌표, 마름모 5.7 / 3.7 / 3.6, G0-4 범위·W 자격, d45 1.01, 태그·E-6, G0 재계산, rev4 G1 정의, W 선정·FLAG (i)·(ii), 7절 승계, 등급 정의)은 바꾸지 않는다.
- 규약·기호·$F_{D8}$ = 14,414.589 N은 원판과 같다. K1 = LAS-b K1(R4c30 순서 관문).

## 공개: 봉인 시점에 본 것과 없는 것

| 구분 | 내용 |
|---|---|
| 본 것 | rev4 공개 목록, rev4 봉인 점검 원문 전체, 탐침 보존 폴더의 다섯 파일과 `SHA256SUMS.txt`(1절 표의 값), 경로 2 `d8x_recount.py`(`46010967…`) V-2(1306~1320행)·`grade`(1552~1575행), 브랜치 `d8x-gate-meta` 커밋 제목(4e8eb9b) |
| 없는 것 | 정식 R-a·R-c·Chrono·G0 rev3 산출물은 0건이다. 1절의 탐침 3건(파이프라인 점검, 판정 아님)이 새 점에 대해 이 판 작성자가 본 유일한 폐루프 값이다 |

## 1. A-1: 탐침 3건 공개와 rev4 문구 정정

### 1.1 정정

- rev4 "공개" 절의 "**R-a·R-c·Chrono D8x 결과와 G0 rev3 결과는 여전히 0건이다.** 새 점의 폐루프·정적 결과를 하나도 보지 않았다"는 **사실과 달랐다.** rev3 봉인(11:36:17) 뒤·rev4 봉인(11:56:17) 전에 구현 에이전트의 파이프라인 탐침 3건이 있었다. rev4 작성자(control-expert)는 rev4를 쓸 때 이 파일을 보지 않았지만, 봉인 시점에 결과가 존재했다. 정확한 문구는 "정식 R-a·R-c·Chrono·G0 rev3 산출물 0건, 판정에 쓰지 않는 탐침 3건 있음(rev5 1.2)"이다.
- rev3 "공개"의 "0건"은 참이다(세 탐침 모두 rev3 봉인 뒤, 재감사 `timeline.py` 확인).

### 1.2 탐침 3건

- 보존 위치: `C:\workspace\outrigger_control\.local_archive\session_6f3ebc4d_20261110\d8x_probes\`(원래 메인 세션 scratchpad `…\scratchpad\d8xfix\`). 파일 sha256(`SHA256SUMS.txt`):

| 파일 | sha256 |
|---|---|
| `ra_probe_off.json` | `43da9a8888f8d08bc496e6708db89d8e9853f5b3658433ea98d59110d29b4e23` |
| `ra_probe_off.log` | `6bf91694e8cf2facf4b082ce14b4aa91e73fe6a8cee9e59befef48f9afc4afa5` |
| `rc_probe_off.json` | `327ef5cceae01fce74e2410df54f6dae36489f24c913410d24965dc39358445b` |
| `rc_probe_on.json` | `97fa70ad5b0bd646b4f7d7811f1489de6b0b24211b98b97fa8531ebcf5c5a2f0` |
| `rc_probe.py` | `93a47b6fba7f67736eacde299d007f69614dab39d7477b7b77dc0753f333c4a3` |

| 탐침 | 시각(mtime, +09:00) | 키 | 팔·태그 | 값 |
|---|---|---|---|---|
| R-a | 11:39:53(경과 124 s) | `main\|C2_tv0.1\|top\|rigid\|pitch+`(pitch+ 3.7°, td_main 상단 rigid) | K1 끔, `final_C4G2_LAS`, `k1_order_gate` false | `min_true_cyl_force_kN` 61.0, `t_ready_s` 43.4, `commands_sha256` `cab74a24…be23` |
| R-c 끔 | 11:39:42(126.7 s) | `D1\|H-R-X\|rigid\|T\|fdown3.7\|K1`, VB, ε 0 | K1 끔, `final_C4G2_P3_LAS`, `k1_order_gate` false, LAS-b 켬 | `J1_N` 53,835.95, `t_ready_s` 57.5 |
| R-c 켬 | 11:42:25(157.7 s) | 같은 키, VB, ε 0 | K1 켬, `final_C4G2_P3_LAS_K1`, `k1_order_gate` true, LAS-b 켬 | `J1_N` 53,835.95, `t_ready_s` 57.5 |

- 실행 커밋: 통합 브랜치 `20e8722`(`worktree-agent-ac6cd65fc4ec57212`), `is_clean: false`(미커밋 구현 편집 중). R-a는 `d8x.limit` 1. 스크립트 `rc_probe.py` docstring "Pipeline probe (not a judged run)". (R-c 키 끝의 `K1`은 하네스 키 토큰 = 크롤러 강성 ×1이다. LAS-b K1과 다르다.)
- **판정에 쓰지 않는다**(rev4 3: 통합 브랜치 병합 전 커밋의 결과, 그리고 dirty 트리라 원판 I-1 불충족). 같은 키의 정식 행은 $H_{impl}$에서 새로 돈다.
- 영향: rev4가 바꾼 것은 판정 범위(K1 켬 팔 `fail` → G1 실패)뿐이고, 명령·실행과 무관하며 엄격한 쪽이다. 본 값이 rev4·rev5의 선택을 덜 엄격한 쪽으로 움직이지 않았다. rev5 2절(A-2 (b))도 (a)보다 같거나 엄격한 쪽이다.

## 2. A-2: V-2 판정 대상에 K1 켬 팔 포함 (원판 7 V-2·V-2b 읽기)

- 원판 V-2 "R-a·R-c **판정 대상 행**의 `INFO_LIFTOFF_SLOW` 수를 점·단계별로 센다"의 판정 대상은 rev4 1.1의 정의다: **R-a 1,102 전부(K1 끔 910 + K1 켬 192)와 R-c 288 전부(끔 192 + 켬 96).**
- 한 점·단계에서 두 팔 중 어느 쪽이라도 수가 0보다 크면 그 점은 `LAS_DEPENDENT`(V-2b) → 원판 10 FLAG (iii), V-2b의 Chrono 재실행 대상이다. 두 팔 모두 0인 점만 `LAS_INACTIVE`다.
- 수를 셀 때 키는 (묶음, 점, 단계)이고, 사건 이름 접두사는 `INFO_LIFTOFF_SLOW`다(경로 2 `LAS_EVENT_PREFIX`와 같음).

### 2.1 판정서 손 적용 (두 도구는 끔 팔만 센다)

- 경로 2 `invariance()` V-2(1306~1320행, 주석 "judged rows only (K1 pairs excluded)")와 경로 1 `_las_activity(ra_off, rc_off)`는 끔 팔만 센다. 경로 2는 고치지 않는다. 경로 1은 고쳐도 된다.
- **판정서 의무 절차**
  1. K1 켬 팔 행의 `INFO_LIFTOFF_SLOW` 수를 (묶음, 점, 단계)별로 센다. 경로 2는 `report["ra"]["on"]["rows"][*]["record"]["las_events"]`·`report["rc"]["on"]["rows"][*]["record"]["las_events"]`, 경로 1은 켬 팔 행의 사건 이름 목록에서 센다. 필드가 없으면 원 결과 파일(R-a 런의 사건 이름 목록, R-c `d1` 사건 이름 목록)에서 손으로 센다.
  2. 두 경로의 켬 팔 수가 하나라도 다르면 원판 8절 불일치(판정 불가)다.
  3. 끔 팔의 도구 결과(`V-2.LAS_DEPENDENT`)와 켬 팔 손 집계의 합집합을 V-2 결과로 적는다. 도구가 `LAS_INACTIVE`인데 켬 팔에 작동한 점이 있으면 "A-2 손 적용: 도구 LAS_INACTIVE → LAS_DEPENDENT(점 목록)"을 적고, 등급의 FLAG (iii)와 V-2b Chrono 재실행 목록에 넣는다.
  4. 경로 1을 고쳐 켬 팔을 센다면 그 출력이 1~3의 손 적용 결과와 같은지 확인하고 적는다.

## 3. A-3: 손 적용의 순서와 결측 처리 (rev4 1.4 명확화)

### 3.1 정한 문구

1. **도구 판정 불가가 우선한다.** 어느 한 경로라도 R-a 또는 R-c 묶음(또는 G1)을 `판정 불가`로 내면, rev4 1.4의 F-1 손 적용으로 그 묶음을 `fail`로 바꾸지 않는다. K1 켬 팔 `fail` 수는 기록만 한다. 이유: 원판 10 판정 불가(정체성·빈 집합·두 경로 불일치)는 원인 수정 뒤 재실행(B-ID) 대상이고, 정체성이 깨진 행으로 등급을 내지 않는다.
2. **도구 보류는 판정이 아니다.** 어느 경로가 G1을 `보류(입력 미완)`로 내면 판정서를 쓰지 않는다(입력을 채운 뒤 다시 집계). 판정서의 최종 집계는 원판 3절의 모든 입력(R-a 끔·켬, R-c 끔·켬, G0, Chrono)이 들어간 실행에서만 한다.
3. **결측은 판정 불가다.** 최종 집계에서 경로 2 `bundles["R-a"|"R-c"]["k1_rows_fail"]`이 `None`이거나, 경로 1 출력에 `k1_rows_failed` 키가 없으면 그 묶음은 `판정 불가`(입력 누락 또는 도구 출력 결함)다. 0으로 읽지 않고, "0이 아님"(`fail`)으로도 읽지 않는다.
4. **두 경로 수 대조.** 1~3에 해당하지 않으면 두 경로의 켬 팔 `fail` 수(경로 2 `k1_rows_fail`, 경로 1 `len(k1_rows_failed)`)를 비교한다. 다르면 원판 8절 불일치(판정 불가)다.
5. **F-1 적용.** 같고 0보다 크면 그 묶음의 G1은 `fail`이다. 같고 0이면 도구의 G1을 그대로 쓴다.
6. **등급.** 손 적용 뒤의 관문 상태로 등급을 다시 매긴다. 순서는 원판 10·경로 2 `grade()`와 같다: 판정 불가 > 미달 > 보류 > 조건부 통과 > 통과. 따라서 G1이 손 적용으로 `fail`이어도 다른 관문(G0, G2a, G2b, G-S)이 `판정 불가`면 등급은 `판정 불가`이고, G1 `fail`은 기록된다. rev4 1.4-2의 "도구 출력과 관계없이 `미달`"은 이 순서로 읽는다(G1 `fail`이 미달로 이끄는 것은 그대로).
7. V-2 손 적용(2.1절)도 같은 순서다: 결측(켬 팔 행 기록 없음)·두 경로 불일치는 판정 불가, 그 밖은 2.1-3대로 FLAG (iii)에 넣는다.

- 감사 제안과의 차이: 감사는 "도구 G1이 판정 불가·보류이면 그것이 우선"이라고 했다. 이 판은 판정 불가는 그대로 우선으로 두고, **보류는 "판정서를 쓰지 않음"으로 정했다.** 보류는 입력이 다 들어오지 않은 중간 상태라 등급이 아니기 때문이다. 감사의 "None·키 없음은 판정 불가"는 최종 집계에서 그대로 채택했다(중간 집계에서 `None`은 보류와 같이 나타난다).

### 3.2 판정서 표 (의무)

| 경로 | 묶음 | K1 켬 팔 expected | actual | pass | fail | unjudgeable | 도구 G1 | 손 적용 G1 |
|---|---|---|---|---|---|---|---|---|
| 경로 1 | R-a | 192 | | | | | | |
| 경로 1 | R-c | 96 | | | | | | |
| 경로 2 | R-a | 192 | | | | | | |
| 경로 2 | R-c | 96 | | | | | | |

- 경로 2 값은 `bundles[<묶음>]["parts"]["on"]`(`count_rows`의 expected/actual/pass/fail/unjudgeable)과 `k1_rows_fail`, 경로 1 값은 켬 팔 `summaries`와 `k1_rows_failed` 길이에서 옮긴다. 끔 팔도 같은 열로 함께 적는다.
- V-2 표: (묶음, 점, 단계)별 끔 팔 수(도구) / 켬 팔 수(경로 1, 경로 2) / 분류.

## 4. A-6: $H_{impl}$ 지정 (rev4 3 문구 대체)

- rev4 3의 "그 커밋 id는 D8x 실행 전 감사에서 지정"은 **"$H_{impl}$ 커밋은 메인 세션이 지정하고 실행 전 감사가 확인한다"**로 대체한다. 지정한 커밋 id는 실행 전 기록과 판정서 시간 순서 절에 적는다. $H_{impl}$의 정의(통합 브랜치 `worktree-agent-ac6cd65fc4ec57212`를 master에 병합한 뒤의 master HEAD)는 rev4 그대로다.

## 5. Chrono E-6d가 읽는 기록 키 (rev3 3.1 E-6d 보충)

- cad-expert가 Chrono 행 기록 키를 넣었다(브랜치 `d8x-gate-meta` 4e8eb9b, 병합 전). E-6d Chrono 판정(경로 1)은 다음을 읽고 모두 참이어야 한다.
  - `d8x.k1_order_gate`(실제 제어기 값) is True
  - `d8x.controller_meta_order_gate` is True
  - `d8x.k1_order_gate_matches_meta` is True
  - `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate` is True
  - 실행 전 기록 `d8x_prelaunch_C.json`의 `rows[<case>].k1_order_gate`가 True(켬 팔)로 적혀 있음
- 키가 없으면 그 행은 판정 불가다. 경로 2는 이 키를 보지 않는다(rev3 3.3, rev4 2의 범위 차이 문구 그대로).
