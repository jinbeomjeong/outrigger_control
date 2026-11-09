# K1 조건부 채택 판정서 — 저장 Chrono SCM 결과의 그림자 dP

- 작성: control-expert, 2026-11-09
- 상태: **판정 후 감사 반영판(차단 0, 기록 5, 독립 재집계 일치).** 문구만 고쳤고 등급·수치는 그대로다.
- **최종 판정: `판정 불가`**(규칙 6.2절)
  - 판정 도구(경로 1): `grade` "판정 불가", `grade_code` `undecidable`, 종료 코드 1, 실패한 K 검사 없음.
  - 두 경로 재집계(K-9): 의미가 다른 차이 **0건**, 형식만 다른 차이 1건(행 경로 표기, 8절). 그래서 K-9는 참이고, 등급은 stop이 아니라 `판정 불가`로 확정한다.
- 근거(한 줄): MUST 31 LOC 가운데 **셀 수 있는 13건은 모두 dP > 0**(+49~+209)이다. 그러나 **18건은 `UNRECOVERABLE`**이다. 18건 모두 R4 평가 LOC가 뒤에 취소되고(`INFO_LOC_REVOKED`) 새 LOC가 와서, 저장 메타에 그 LOC의 $t_P$가 남지 않았다(규칙 4.3 (c)).
  - 6.2절 순서상 `미달`이 먼저다. 그러나 MUST에 dP ≤ 0인 LOC나 `BLOCKED_MISSING` LOC가 없어 `미달`에 해당하지 않는다. 그다음 조건인 "MUST에 `UNRECOVERABLE` ≥ 1"이 걸려 `판정 불가`가 된다.
- 규칙 6.2절 행동: **전환하지 않는다**(프리셋·태그 그대로). 건수와 행을 공개하고(3절), 선택지는 사용자에게 묻는다(14절). 새 실행은 사용자 승인 뒤에만 한다.
- 꼭 공개할 것
  - ② PATCH 조건은 참이지만 **봉인 전 기지 행(S-Ch 2행)뿐**이다(4절).
  - `B_SOFT_NONPOS` **3행**(집합 B, 옛 제어기, 모두 dP = 0)(5절).
  - 사전 예측 P-6·P-9·P-10(과 경로 1 판정의 P-2)이 범위 밖이다(7절).
- 규약
  - 제어: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 다리 행정 속도 명령 [m/s]).
  - 시각은 Chrono 절대 시각 [s]이다. 비교는 모두 정수 주기 $n = \mathrm{round}(t/0.1)$로 한다(규칙 4.1, Python 내장 `round`).
  - 이름 구분: 이 판정의 K1 = LAS-b K1(R4c30 순서 관문, `flat_soil_margin_order_gate`)이다. 2026-11-05에 탈락한 touch-phase K1과 다르고, 하네스 키 토큰 `K1`(크롤러 강성 ×1)과도 다르다.

| 기호 | 정의 | 단위 |
|---|---|---|
| LOC | 크롤러 이탈 확정(사건 `crawler_liftoff_confirmed`) | — |
| R4 평가 LOC | R4c30 조건이 참이었던 LOC(사건 `INFO_LOC_FLAT_SOIL_MARGIN` 또는 `…_SKIPPED:order`) | — |
| $n_R$ | R4 평가 LOC의 주기 | 주기 |
| $t_P$, $n_P$ | 그 LOC를 확정한 S-1 평탄 창 꼬리의 첫 표본 시각(`soil.t_P_s` 또는 decision `t_P_s`), 그 주기 | s, 주기 |
| $t_S$, $n_S$ | 그 LOC 시점의 가장 최근 토양 모드 시작(주기 < $n_R$), 그 주기 | s, 주기 |
| dP | $n_P - n_S$. K1은 dP ≤ 0이거나 $t_P$가 없으면 R4c30을 막는다 | 주기 |
| 출처 a/b/c | (a) decisions, (b) 최종 LOC = R4 LOC라서 `soil.t_P_s`, (c) 그 밖 = 복원 불가 | — |

## 0. 규칙·실행 정체성·파일

### 0.1 규칙

| 파일 | sha256 | 봉인 시각 | 봉인 커밋(커밋 시각) |
|---|---|---|---|
| `las_k1_rules_adopt.md` | `864836d852b4a783a577f01f738536b7c30c574bf4bebb3b0219e68e59b07ea8` | 2026-11-09 22:05:43 +09:00 | `3f5d519`(22:07:00) |

- `.sha256` 기록과 같다. 경로 1(K-0)과 경로 2가 각각 다시 계산했다.
- 이어받는 규칙: K1 원판 `2742c976…e4a0`, rev1 `eeee4ab9…b4d3`, S-Ch 계획 `b0fe744f…6d9d`·rev1 `d8f957cb…9295`.

### 0.2 실행 정체성

| 항목 | 경로 1 (판정 도구) | 경로 2 (독립 재집계) |
|---|---|---|
| 실행자 | 메인 세션 | control-expert |
| 파일 | `06_analysis/02_control/verif_matrix/scripts/las_k1_adopt_judge.py` | `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\k1adopt_p2\recount_adopt.py` |
| 도구 sha256 | `7c68ca78a7f41310bf405b34fb507c0419195326bc19ba19a56b79e7b400cde7`(`--expect-tool-sha`로 실행 시 확인, 지금 파일도 같음) | `bcec79296ea68b87ddf174cd3148a92ff10edc19ab20a69bd1241e2f95fc7d8a` |
| 도구 커밋 | `45f3c8c`(22:19:00), 병합 `859deef`(22:20:14) | 커밋 없음(scratchpad) |
| 환경 | dynamics-dev `python.exe -I -B`, PowerShell | 같음 |
| 명령 | `las_k1_adopt_judge.py list` → `judge --expect-tool-sha 7c68ca78…cde7` | `recount_adopt.py --out <…>\recount_adopt.json` |
| 종료 | list 0(8개 비교 모두 참, `post_seal_new_files` 0) / judge 1 | 1 |
| 출력 | `06_analysis/03_hydraulic/coupled/v5/las/k1/judge_adopt.json` `da8aaeebd2a06518b52112424339f4cf62af109e614fd3c2165e84ed7ebf3812`(22:32:52) | `…\k1adopt_p2\recount_adopt.json` `ded4a30e99c302348841ed332a2948e324e2b9fb1edae5a818837df2e95fa2d5`(22:30:30) |
| 목록 출력 | `…/k1/adopt_list.json` `7abc0485736dcfae92ef327a84359af8f50631c1a14353e6eaeef6b14f33cc6b`(22:32:29) | 같은 내용을 `sets_rebuilt`에 담음 |
| HEAD | `859deef20aa17c2789a5cd2f55c901bb8ba7d410` | 같음 |
| 사용 모듈 | 표준 라이브러리만(프로젝트 모듈·다른 판정 도구 import 없음) | 표준 라이브러리만(json, hashlib, re, statistics, argparse, subprocess로 `git rev-parse` 1회) |

- 실행 때 main 작업 트리: 추적 파일 수정 2건(`04_scripts/02_chrono/render_S2_gifs.py`, `06_analysis/01_chrono/12_S2/S2_gifs.json`)이 있었다. 둘 다 S2 그림 작업이고 이 판정이 읽는 파일이 아니다. 그 밖은 추적하지 않는 파일 15건이다(`judge_adopt.json` `git_head.status_porcelain`).
- 경로 2는 경로 1 실행 전에 출력 sha를 고정해 메인 세션에 넘겼다. 메인 세션은 그 sha를 받은 뒤 경로 1을 실행했다(9절). 경로 2는 경로 1 도구를 열지도, import하지도, 실행하지도 않았다. 경로 1 출력은 sha 고정(22:32:07 전달) 뒤, K-9 대조 직전(22:33:21)에 키 구조만 확인했다(`p1_keys.py`, 지움). 경로 2 출력은 이미 sha가 고정돼 있어 독립성은 유지된다(판정 후 감사가 transcript로 확인).
- 경로 2의 출력은 결정적이다. 두 번 실행한 출력 sha가 같았다. 출력에 시각은 없지만 HEAD는 들어 있다.

### 0.3 읽은 파일

- 규칙 파일 1개와 result.json 117개(A 74 + B 43)다. 행별 sha256은 `judge_adopt.json` `files_read_sha256`과 `recount_adopt.json` `files_read_sha256`에 있다. 117개 모두 부록 A·B의 sha와 같다(K-2, 경로 2는 B도 대조).
- 모집단 U 300개는 K-1 목록 재구성을 위해 두 경로 모두 읽었다. 행별 값은 판정에 쓰지 않는다.

## 1. 정체성·일관성 K 검사 (규칙 5절)

| # | 경로 1 | 경로 2 | 비고 |
|---|---|---|---|
| K-0 | 참 | 참 | 규칙 sha = `.sha256`. 도구 sha는 실행 전 확인값 = 실행 기록 = 지금 파일(경로 1) |
| K-1 | 참 | 참 | U 300 `41e01c20…`, A 74 `2e7a1a5f…`, B 43 `50622923…`, E 183 `ae171b43…`(`not_run_S9_level` 150, `soil_response_off` 33). 부록 A 파싱 74행, 목록 sha 같음. 봉인 뒤 새 파일 0 |
| K-2 | 참 | 참 | A 74행 파일이 있고 sha가 같다 |
| K-3 | 참 | 참 | 부분 기록 없음, `restored_from` 모두 None |
| K-4 | 참 | 참 | `period_s` 0.1 |
| K-5 | 참 | 참 | R4 LOC 주기가 모두 LOC 사건 목록에 있고, 한 주기에 R4 사건이 둘 이상인 곳은 없다 |
| K-6 | 참 | 참 | S-Ch 2행: decision 1건, 주기 집합 같음. gateoff에 `SKIPPED:order` 없음. gateon에 적용 사건 없음 |
| K-7 | 참 | 참 | `controller_meta.soil` = `c2_soil`(세 키), decisions 최종 LOC `t_P_s` = `soil.t_P_s` |
| K-8 | 참 | 참 | 모든 R4 LOC에 주기 < $n_R$인 토양 모드 시작이 있다. 경로 1(사건)과 경로 2(`mode_starts` → `soil_mode_t_s` → 사건)의 $n_S$가 같다(33/33). decision `t_S_s` 주기와도 같다 |
| K-9 | (외부) | — | **참**. 8절 대조 |

## 2. 대상 집합

| 집합 | 건수 | 목록 sha256 | 분류 |
|---|---|---|---|
| U | 300 | `41e01c20…cd79` | — |
| A | 74 | `2e7a1a5f…a9d2` | UNIFORM_SOFT 50, PATCH 6, UNIFORM_G1 18 |
| B | 43 | `50622923…61c9` | UNIFORM_SOFT 31, PATCH 10, UNIFORM_G1 2 |
| E | 183 | `ae171b43…d473` | — |

### 2.1 A 행 분류 결과

| 행 분류 | 행 수 | R4 평가 LOC | 비고 |
|---|---|---|---|
| MUST | 31 | 31 | 모두 평지(경사 0/0). 경사 UNIFORM_SOFT 18행은 모두 NONE |
| PATCH | 2 | 2 | S-Ch gateoff·gateon(같은 LOC, 고유 LOC 1). **D1-CHRONO 2행·FINAL4 2행은 토양 모드가 없어 NONE** |
| NEUTRAL_G1 | 0 | 0 | G1 균일 18행 모두 토양 모드 없음 |
| NONE | 41 | 0 | 토양 모드 없음 38, E3c10 3(RV6 3행) |

- R4 평가 LOC가 있는 행은 33행이고, 행마다 1건씩이다(`MULTI_LOC` 없음).
- E3c10(`INFO_LOC_CLEARANCE_MARGIN`) LOC는 모두 5건이다(RV6 3 + FINAL-C4G2·FINAL-REP `S9SL_X6rb_rm2p86` 각 1). 뒤의 2건은 토양 모드가 없어 NONE 이유가 "토양 모드 없음"이다(11.2절 #5).
- 토양 모드를 쓴 행은 36행이다.

## 3. LOC별 결과

### 3.1 MUST — `OK` 13건 (모두 dP > 0)

| # | 행(07_results/S9/ 기준) | 토양·오거·질량 | 태그 | $n_R$ | 출처 | $n_P$ | $n_S$ | dP |
|---|---|---|---|---|---|---|---|---|
| 1 | `batch_COUPLED_eta085_20261104_142213/P3b_J1_B_top_Fs4` | J1·상단·1.0 | final_SGS_R4 | 417 | b | 400 | 351 | **+49** |
| 2 | `batch_FINAL-C4G2_20261105/P3b_J1_B_top_Fs4` | J1·상단·1.0 | final_C4G2 | 400 | b | 384 | 333 | +51 |
| 3 | `batch_FINAL-REP_20261030_223359/P3b_J1_B_top_Fs4` | J1·상단·1.0 | final_SGS_R4 | 400 | b | 384 | 333 | +51 |
| 4 | `batch_FINAL6_20261031_000833/P3b_J2_B_top_Fs4_sgRRd150` | J2·상단·1.0 | final_SGS_R4 | 559 | b | 543 | 492 | +51 |
| 5 | `batch_JOURNAL-AUGER_20261031_165543/P3b_J1_B_bottom_Fs4` | J1·하단·1.0 | final_SGS_R4 | 400 | b | 384 | 333 | +51 |
| 6 | `batch_JOURNAL-AUGER_20261031_165543/P3b_J1_B_middle_Fs4` | J1·중단·1.0 | final_SGS_R4 | 400 | b | 384 | 333 | +51 |
| 7 | `batch_V5-PROBE_20261106/probe_flow` | J1·상단·1.0 | final_C4G2 | 417 | b | 400 | 351 | **+49** |
| 8 | `batch_V5-PROBE_20261106/probe_valve_m2` | J1·상단·1.0 | final_C4G2 | 399 | b | 383 | 333 | +50 |
| 9 | `batch_V5-PROBE_20261106/probe_vb` | J1·상단·1.0 | final_C4G2 | 417 | b | 401 | 351 | +50 |
| 10 | `batch_V5-PROBE_QUIET_20261107/probe_vb_quiet` | J1·상단·1.0 | final_C4G2 | 417 | b | 401 | 351 | +50 |
| 11 | `batch_V5-STAGE3_20261107_184239/P3b_J1_B_top_Fs4` | J1·상단·1.0 | final_C4G2 | 417 | b | 401 | 351 | +50 |
| 12 | `batch_V5-STAGE3_20261107_184239/P3b_J1_B_top_Fs4_v0v` | J1·상단·1.0 | final_C4G2 | 399 | b | 383 | 333 | +50 |
| 13 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180_seed20261029` | J2·상단·1.1 | final_C4G2 | 554 | b | 540 | 331 | +209 |

- 모두 패드 B, F_s 4 kN, 경사 0/0이다. 13건 모두 LOC 취소가 없는 행이다.
- 분포: 최소 +49, 중앙 +50, 최대 +209. 히스토그램(5주기 폭): [45,50) 2, [50,55) 10, [205,210) 1.
- (case, 태그)별 최소: `P3b_J1_B_top_Fs4|final_SGS_R4` 49, `probe_flow|final_C4G2` 49, 그 밖 50~51, `…_seed20261029|final_C4G2` 209.
- `THIN_MARGIN`(dP ≤ 12)은 0건이다. 셀 수 있는 MUST LOC의 최소 여유는 49주기다(문턱 0 대비, S-Ch에서 본 치우침 12주기의 약 4배).

### 3.2 MUST — `UNRECOVERABLE` 18건 (모두 `REVOKED_AFTER_R4`)

| # | 행 | 토양·오거·질량 | 태그 | $n_R$ | $n_S$ | 취소 주기 | 다음 LOC 주기 |
|---|---|---|---|---|---|---|---|
| 1 | `batch_COUPLED_eta085_20261104_142213/P3b_J2_B_top_Fs4_m1p1_t180` | J2·상단·1.1 | final_SGS_R4 | 563 | 351 | 571 | 580 |
| 2 | `batch_FINAL-C4G2_20261105/P3b_J1_B_top_Fs4_m1p1` | J1·상단·1.1 | final_C4G2 | 492 | 333 | 497 | 509 |
| 3 | `batch_FINAL-C4G2_20261105/P3b_J2_B_middle_Fs4` | J2·중단·1.0 | final_C4G2 | 451 | 332 | 454 | 465 |
| 4 | `batch_FINAL-C4G2_20261105/P3b_J2_B_top_Fs4` | J2·상단·1.0 | final_C4G2 | 451 | 332 | 454 | 465 |
| 5 | `batch_FINAL-C4G2_20261105/P3b_J2_B_top_Fs4_m1p1` | J2·상단·1.1 | final_C4G2 | 553 | 333 | 566 | 574 |
| 6 | `batch_FINAL-REP-X_20261031_020716/P3b_J2_B_top_Fs4_m1p1_t180` | J2·상단·1.1 | final_SGS_R4 | 553 | 333 | 566 | 574 |
| 7 | `batch_FINAL-REP_20261030_223359/P3b_J1_B_top_Fs4_m1p1` | J1·상단·1.1 | final_SGS_R4 | 492 | 333 | 497 | 509 |
| 8 | `batch_FINAL-REP_20261030_223359/P3b_J2_B_middle_Fs4` | J2·중단·1.0 | final_SGS_R4 | 451 | 332 | 454 | 465 |
| 9 | `batch_FINAL-REP_20261030_223359/P3b_J2_B_top_Fs4` | J2·상단·1.0 | final_SGS_R4 | 451 | 332 | 454 | 465 |
| 10 | `batch_FINAL-REP_20261030_223359/P3b_J2_B_top_Fs4_m1p1` | J2·상단·1.1 | final_SGS_R4 | 553 | 333 | 566 | 574 |
| 11 | `batch_JOURNAL-AUGER_20261031_165543/P3b_J2_B_bottom_Fs4` | J2·하단·1.0 | final_SGS_R4 | 451 | 332 | 454 | 466 |
| 12 | `batch_V5-PROBE_20261106/probe_vb_m1c_vn` | J1·상단·1.0 | final_C4G2 | 500 | 367 | 507 | 529 |
| 13 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180` | J2·상단·1.1 | final_C4G2 | 588 | 375 | 599 | 607 |
| 14 | `…/P3b_J2_B_top_Fs4_m1p1_t180_seed20261026` | J2·상단·1.1 | final_C4G2 | 553 | 333 | 566 | 574 |
| 15 | `…/P3b_J2_B_top_Fs4_m1p1_t180_seed20261026_flow` | J2·상단·1.1 | final_C4G2 | 563 | 351 | 571 | 580 |
| 16 | `…/P3b_J2_B_top_Fs4_m1p1_t180_seed20261027` | J2·상단·1.1 | final_C4G2 | 547 | 330 | 560 | 568 |
| 17 | `…/P3b_J2_B_top_Fs4_m1p1_t180_seed20261028` | J2·상단·1.1 | final_C4G2 | 546 | 331 | 558 | 566 |
| 18 | `…/P3b_J2_B_top_Fs4_m1p1_t180_v0v` | J2·상단·1.1 | final_C4G2 | 553 | 332 | 566 | 574 |

- 14~18의 배치는 `batch_V5-STAGE3_20261107_184239`다.
- 출처는 모두 (c)다. $n_R \ne n_{fin}$이고 decisions가 없어 $t_P$가 남지 않았다. $n_P$·dP는 비워 둔다. 규칙 4.3 (c), 11절 #8에 따라 재구성하지 않는다.
- 취소 주기와 다음 LOC 주기는 판정 뒤에 사건 목록에서 읽은 기록이다(13절). 판정에는 쓰지 않는다.
- 고유 조건은 7종이다: J2 상단, J2 중단, J2 하단, J2 상단 ×1.1, J2 상단 ×1.1 t180(시드·유량·v0v 변형 포함), J1 상단 ×1.1, J1 상단 `probe_vb_m1c_vn`.
- **같은 조건의 OK 행과 비교**(기록): J1 상단 ×1.0(OK 11건, dP +49~+51)은 취소가 없었다. J1·J2 ×1.1과 J2 ×1.0은 R4 LOC가 거의 늘 취소됐다. 예외는 OK #4(J2 상단 `sgRRd150`)와 OK #13(J2 ×1.1 seed20261029)이다. 그래서 **복원 불가 18건은 J2와 질량 ×1.1 쪽에 몰려 있고, 셀 수 있는 13건은 대부분 J1 ×1.0이다.** 셀 수 있는 LOC의 dP가 모두 크다는 사실을 복원 불가 조건으로 넓혀 읽을 수 없다.

### 3.3 PATCH — `OK` 2건 (봉인 전 기지 행)

| 행 | 태그 | $n_R$ | 출처 | $t_P$ [s] | $t_S$ [s] | $n_P$ | $n_S$ | dP | 기지 행 |
|---|---|---|---|---|---|---|---|---|---|
| `batch_V5-LAS-K1-CHRONO_20261109_193952/SCh_G1_J2FL_B_top_Fs4_VB_gateoff` | final_C4G2_P3_LAS | 377 | a | 34.9 | 36.9 | 349 | 369 | **−20** | 예 |
| `…/SCh_G1_J2FL_B_top_Fs4_VB_gateon` | final_C4G2_P3_LAS | 377 | a | 34.9 | 36.9 | 349 | 369 | **−20** | 예 |

- $t_S$는 경로 2에서 `mode_starts`, 경로 1에서 사건으로 얻었고 같다. S-Ch 판정서 1.2절 값과도 같다.

## 4. 판정 조건 (규칙 6.1)과 등급 (6.2)

| 조건 | 값 | 판단 |
|---|---|---|
| ① MUST: `OK` ≥ 1 | 13 | 참 |
| ① MUST: 모든 LOC가 `OK`이고 dP > 0 | 13/31만 `OK`, 18건 `UNRECOVERABLE` | **거짓** |
| ② PATCH: `OK`+`BLOCKED_MISSING` ≥ 1 | 2 | 참 |
| ② PATCH: 모든 LOC가 dP ≤ 0 또는 `BLOCKED_MISSING` | 2/2(−20, −20) | 참 |
| ② 기지 행 제외 | PATCH LOC 0건(D1-CHRONO·FINAL4는 R4 LOC 없음) | **"기지 행뿐"**(6.1 공개 조항) |

| 등급(위에서부터) | 조건 | 해당 |
|---|---|---|
| `stop` | K-0~K-9 중 거짓 | 아님(모두 참, K-9는 8절) |
| `미달` | MUST에 `OK`·dP ≤ 0 또는 `BLOCKED_MISSING` ≥ 1 | 아님(0건) |
| **`판정 불가`** | MUST `OK` 0건, 또는 MUST `UNRECOVERABLE` ≥ 1 | **해당**(18건) |

- 경로 1 `grade_reasons` 18줄은 위 18건을 하나씩 든다. 경로 2 사유는 "MUST OK=13, UNRECOVERABLE=18"이다.
- 판정 뒤 문턱(dP > 0, `THIN_MARGIN` 12)은 바꾸지 않았다.

## 5. FLAG (규칙 7절, 등급 영향 없음)

| FLAG | 값 | 내용 |
|---|---|---|
| `THIN_MARGIN` | 0 | 셀 수 있는 MUST 최소 dP +49 |
| `NEUTRAL_G1_BLOCK` | 0 | NEUTRAL_G1 LOC 0 |
| `MULTI_LOC` | 0행 | — |
| `REVOKED_AFTER_R4` | **18행** | 3.2절의 18행과 같은 집합 |
| `B_SOFT_NONPOS` | **3행** | 아래 |

### 5.1 `B_SOFT_NONPOS` 3행 (반드시 공개)

| 행(집합 B, 옛 제어기, R4c30 없음) | 토양·질량 | $n_{fin}$ | $n_P$ | $n_S$ | dP |
|---|---|---|---|---|---|
| `batch_D424R_20261030_073635/P3b_J1_B_top_Fs4_m1p1` | J1·1.1 | 513 | 502 | 502 | **0** |
| `batch_D424_20261030_014908/P3b_J1_B_top_Fs4_m1p1` | J1·1.1 | 514 | 502 | 502 | **0** |
| `batch_RV1_20261030_111615/P3b_J2_B_top_Fs4_m1p1` | J2·1.1 | 576 | 569 | 569 | **0** |

- 뜻: 지금 정의의 K1이 이 LOC에서 R4c30을 평가했다면 **막았을 것이다**(dP = 0 ≤ 0).
- 제한
  1. 집합 B는 R4c30이 없는 옛 제어기(10-27~10-30)다. 정착 기울기 등 R4 조건이 그 LOC에서 참이었는지 알 수 없다. 규칙 7절대로 등급은 바꾸지 않는다.
  2. 세 행 모두 첫 LOC 뒤 LOC 취소가 있었다. 여기서 본 것은 취소 뒤 **두 번째 LOC**(최종 LOC)다. 13절 참고 분석대로, 세 행 모두 $t_P$와 $t_S$가 **같은 float**다. 지금 제어기라면 R4는 첫 LOC(주기 492·492·553)에서 평가된다. A의 같은 조건 행(FINAL-REP `P3b_J1_B_top_Fs4_m1p1` 등)도 첫 LOC에서 R4가 섰다.
  - 그래서 이 3행은 "첫 R4 LOC에서 K1이 막는다"는 증거가 아니다. **"LOC 취소 뒤 다시 확정되는 LOC에서는 dP가 0이 된다"는 증거**다. 이것이 채택 판단에 주는 뜻은 14.4절에 있다.

## 6. 집합 B 요약 (기록, 규칙 7절)

| 상태 | 행 수 |
|---|---|
| OK(최종 LOC dP 계산) | 26 |
| 토양 모드 없음(주기 < $n_{fin}$인 시작 없음) | 16 |
| LOC 없음(`t_loc_s` None, `D424 P3b_J1_B_top_Fs4_m1p2`) | 1 |

| 바닥 | n | 최소 | 중앙 | 최대 | 히스토그램 |
|---|---|---|---|---|---|
| UNIFORM_SOFT | 22 | 0 | 51 | 143 | [0,5) 3, [5,10) 1, [30,35) 2, [35,40) 2, [50,55) 5, [85,90) 2, [100,105) 5, [105,110) 1, [140,145) 1 |
| PATCH | 4 | −20 | 25.5 | 38 | spJ2FL −20(기지), spS1FL +20·+31, 패드 A spS1FL +38 |

- UNIFORM_SOFT dP ≤ 5인 행: 3건이 0(5.1절), 1건이 +5(`RV1 S9SL_X4nd_J1_B_top_Fs4_r0_p2p8`, 경사 pitch 2.8°)다. +5는 THIN_MARGIN 범위(≤ 12)에 들지만 집합 B라 FLAG 대상이 아니다(기록).
- **B PATCH의 S1 패치 3행은 dP > 0**(+20, +31, +38)이다. K1이 이 키에서 R4c30을 막지 않을 수 있다는 뜻이다(옛 제어기, 기록). A에는 S1 패치 행이 없다.

## 7. 사전 예측 대조 (규칙 8절, 판정 기준 아님)

| # | 예측 | 관측 | 안/밖 |
|---|---|---|---|
| P-1 | MUST 평지 26~32행, 경사 0행 | 평지 31, 경사 0 | 안 |
| P-2 | MUST dP 모두 > 0, 최소 [+15, +60], 중앙 [+30, +90], 점 예측 최소 ≈ +19 | 셀 수 있는 13건 최소 +49, 중앙 +50, 모두 > 0. 18건은 셀 수 없음 | **밖(경로 1 출력 `inside` 거짓)**. 경로 2 해석: 최소·중앙의 범위 항목은 안이다. "모두 > 0"은 31건 중 13건만 확인돼 성립을 말할 수 없다. 점 예측 +19와는 30주기 차이다 |
| P-3 | `THIN_MARGIN` 0 | 0 | 안 |
| P-4 | PATCH 행(S-Ch 제외) 0~4행, 있으면 dP ∈ [−30, −1] | 0행 | 안 |
| P-5 | NEUTRAL_G1 LOC 0~3 | 0 | 안 |
| P-6 | `UNRECOVERABLE` 0~2건 | **18건** | **밖** |
| P-7 | `BLOCKED_MISSING` 0 | 0 | 안 |
| P-8 | K-0~K-9 모두 참 | K-0~K-8 참(두 경로), K-9 참(8절) | 안 |
| P-9 | `B_SOFT_NONPOS` 0~2건, B 패치 spJ2FL −20 | **3건**, spJ2FL −20 | **밖** |
| P-10 | `통과`(다음 가능성 P-6 때문의 `판정 불가`) | `판정 불가` | **밖**(차선으로 예측한 원인과 같다) |

- P-6이 크게 틀린 원인: 규칙을 쓸 때 메타 키 이름만 보고(1.2절), 값과 무관한 사건 건수(`INFO_LOC_REVOKED`가 R4 LOC 뒤에 있는 행 수)를 세지 않았다. L1gs 취소가 "×1.1 J1 상단 등 일부"에서만 날 것으로 봤지만, 실제로는 J2 ×1.0과 ×1.1에서 거의 늘 났다. 사건 이름 건수는 값을 보지 않고도 봉인 전에 셀 수 있었다(교훈, 15절).

## 8. 두 경로 대조 (K-9)

- 대조 도구: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\k1adopt_p2\k9_compare.py`. 두 출력 파일만 읽는다. 결과는 같은 폴더의 `k9_compare.json`이다.
- 입력 sha를 먼저 확인했다: 경로 1 `da8aaeeb…3812`, 경로 2 `ded4a30e…2d5`. 둘 다 고정값과 같다.
- 허용 오차 없이 비교했다(정수와 저장 float 그대로).

| 대조 항목 | 경로 1 | 경로 2 | 결과 | 종류 |
|---|---|---|---|---|
| 행 경로 표기 | `S9/<배치>/<행>/result.json` | `S9/<배치>/<행>` | 접미사를 떼고 비교 | **형식만 다름** |
| LOC 튜플 (row, $n_R$, source, state, $n_P$, $n_S$, dP) | 33 | 33 | **33/33 완전 일치** | — |
| LOC 저장 float `t_P_s`, `t_S_s` | | | 일치 | — |
| LOC $n_R - n_S$, 기지 행, 분류, 바닥 | | | 일치 | — |
| `rows[].row_class` | 74 | 74 | **74/74 일치** | — |
| `rows[].none_reason` | | | 일치(토양 모드 없음 38, E3c10 3) | — |
| 행별 R4 LOC·E3c10 LOC·취소 건수 | | | 일치 | — |
| `flags.THIN_MARGIN` | [] | [] | 일치 | — |
| `flags.NEUTRAL_G1_BLOCK` | 0 | 0 | 일치 | — |
| `flags.MULTI_LOC` | [] | [] | 일치 | — |
| `flags.REVOKED_AFTER_R4` | 18행 | 18행 | 일치(같은 집합) | — |
| `flags.B_SOFT_NONPOS` | 3행 | 3행 | 일치(같은 집합) | — |
| `grade` | 판정 불가(`undecidable`) | 판정 불가 | **일치** | — |
| 조건 ①·② | ① 거짓, ② 참, 기지 행 제외 0건(`condition_2_known_rows_only` 참) | ① 거짓, ② 참, 기지 행 제외 0건 | 일치 | 기록 |
| 집합 B 행별 ($n_P$, $n_S$, dP) | 43 | 43 | 일치 | 기록 |
| 집합 B 상태 건수 | ok 26 / no_soil_mode 16 / no_loc 1 | OK 26 / NO_SOIL_MODE 16 / NO_LOC 1 | 일치(이름 대소문자만 다름) | 형식만 다름(기록 항목) |

- **UNRECOVERABLE의 $n_S$**: 경로 2는 해석상 UNRECOVERABLE LOC에도 $n_S$를 넣었다(11.2 #1). 경로 1도 같은 값을 넣어서, 이 항목은 차이가 없었다.
- 의미가 다른 차이는 0건이다. **K-9는 참이다.**
- 첫 불일치 뒤 한쪽을 다른 쪽에 맞춘 항목은 없다. 경로 2 출력은 경로 1 실행 전에 sha로 고정했고, 그 뒤 고치지 않았다(규칙 10.2 마지막 항).

## 9. 시간 순서 (2026-11-09, +09:00)

| 시각 | 일 | 근거 |
|---|---|---|
| 22:05:43 | 규칙 봉인(`864836d8…`) | `.sha256` 기록 |
| 22:07:00 | 규칙 커밋 `3f5d519` | git log |
| 22:19:00 | 경로 1 도구 커밋 `45f3c8c`(단위 시험 35개) | git log |
| 22:20:14 | 병합 `859deef` | git log |
| (메인 세션 기록) | verif-protocol-auditor `[시점] 실행 전` 감사(차단 0, 기록 6) | 10절 |
| 22:29:56 | 경로 2 스크립트 최종본(`bcec7929…`) | 파일 시각 |
| 22:26:32 | 실행 전 감사 결과 전달(차단 0) | transcript |
| 22:26:49 | 경로 2 에이전트 시작 | transcript |
| 22:29:50~22:29:56 | 경로 2 스크립트 작성·마지막 수정, 첫 실행 22:29:58 뒤 수정 없음 | transcript |
| 22:30:30 | 경로 2 출력(`ded4a30e…`). 재실행으로 같은 sha 확인 | 파일 시각 |
| 22:32:07 | 경로 2 sha 메인 세션 전달 | transcript |
| 22:32:29 | 경로 1 `list` → `adopt_list.json` | 파일 시각, `taken_utc` 13:32:29Z |
| 22:32:52 | 경로 1 `judge` → `judge_adopt.json`(`da8aaeeb…`) | 파일 시각 |
| 22:33:54~22:33:57 | K-9 대조(`k9_compare.py` → `k9_compare.json`) | 파일 시각 |
| 22:34:54~22:34:58 | 판정 뒤 참고 분석(13절, `posthoc_final_loc.py` → `posthoc_final_loc.json`) | 파일 시각 |

- 봉인 → 도구 → 감사 → 경로 2 → 경로 1 순서가 지켜졌다. 실행 전 감사는 도구 병합(859deef) 직후, 경로 2 착수 전(22:2x, 메인 세션 기록)에 끝났다.

## 10. 실행 전 감사 기록 6건

- 메인 세션이 verif-protocol-auditor `[시점] 실행 전` 감사 리포트(11-09 22:2x, 경로 2 착수 전) 원문에서 옮겼다. 결론: 차단 0 / 실행 전 수정 0 / 기록 6. dirty 작업 트리(추적 수정 2건, S2 그림)는 K-0~K-8에 쓰이지 않는다(`git_head.status_porcelain` 기록만).

| # | 기록 | 처리 |
|---|---|---|
| A-1 | [C/E] `judge`의 등급·종료 코드는 K-9 전 잠정값(K-9 `ok: None` 외부, `decide_grade`는 `ok is False`만 stop) | 경로 2 출력을 경로 1 실행 전에 만들고 sha 고정(`ded4a30e…`), K-9 대조 뒤 등급 확정(8절) |
| A-2 | [R] P-8 "inside"가 K-9 미확정을 참으로 셈 | P-8은 K-9 대조 뒤 적음 |
| A-3 | [R] 구현자 해석 10건은 원문과 맞거나 더 엄격(stop 쪽), 0건 통과 경로 없음 | 11.1절에 목록 공개 |
| A-4 | [I] `judge_adopt.json`은 git 밖(exclude), result.json도 git 밖 → 정체성 근거는 부록 sha(K-2) | 판정서에 `judge_adopt.json` sha256(`da8aaeeb…`) 인용, 파일 보존 |
| A-5 | [S] 시험 파일 `05_tests/unit/test_las_k1_adopt_judge.py`가 `-text` 보호 없음(i/lf w/crlf) | 판정에는 영향 없음(봉인 대상 아님) |
| A-6 | [I] 10.1은 `conda run` 실행, 예정 명령은 exe 직접 호출(표준 라이브러리뿐이라 차이 없음). `git status` 동시 실행 시 `index.lock` 경합 가능, main checkout 경로에서만 실행 | 실제 명령(8절)을 적음. main에서 실행, 경합 없음 |

## 11. 원문 해석 목록

### 11.1 경로 1 구현자(python-expert) 10건

- 메인 세션이 python-expert 구현 리포트(커밋 45f3c8c) 원문에서 옮겼다. 실행 전 감사 A-3이 원문과 대조했다.

1. 정규 목록 경로 형식: `S9/<배치>/<행>/result.json<TAB>sha<LF>`(2.4절 "07_results 기준 상대 경로"). 부록만으로 형식 후보를 시험해 A·B·E·U 네 sha가 모두 재현됐다. E 정규형에는 사유 열이 없다.
2. 봉인 뒤 새 파일(2.6절, K-1): 부록 A∪B∪C(300개)에 없는 파일은 `post_seal_new_files`로 기록만 하고 A·B·E 비교에서 뺀다. 봉인 목록 파일이 없어지거나 바뀌면 sha가 달라져 stop.
3. K-0: `judge`에 `--expect-tool-sha` 필수. 실행 시작·끝 도구 sha와 인자 값이 모두 같아야 한다. 규칙 sha는 봉인값·`.sha256` 첫 토큰과 같아야 한다.
4. K-1 범위 확대: 목록 sha 외에 2.3 분포 값(사유·바닥·평지/경사·태그), 부록 A·B 바닥 분류 열과 도구 분류 일치, 재계산 A와 부록 A의 (경로, sha) 일치, 집합 B 파일 불변.
5. K-3: 부분 기록은 키가 `error` 하나뿐인 dict로만 판단. `restored_from`이 없으면 None. events 항목이 `{t_s: 유한 수, name: str}`가 아니거나 `t_P_s`가 수·None이 아니면 K-3.
6. K-6·K-8: (a) 출처 decision 0건·2건 이상이면 그 LOC는 `UNRECOVERABLE`(어차피 stop). 관문 켬인데 decisions 키가 없으면 K-6 거짓. 경로 2는 4.4절대로 `mode_starts` → `soil_mode_t_s`(주기 ≥ n_R이면 사건으로 대체, 주기 대소 확인), 사건 경로와 다르면 K-8.
7. K-7 최종 LOC decision: `t_loc_s`와 같은 주기의 decision이 있을 때만 `t_P_s` 대조.
8. 고유 LOC 수: (배치, case에서 `_gateoff`·`_gateon`을 뗀 이름, n_R).
9. `REVOKED_AFTER_R4`: 취소 사건 주기 > R4 LOC 주기.
10. 예측 P-1~P-10: 안/밖만 기록(판정 기준 아님).

### 11.2 경로 2(control-expert) 11건

| # | 해석 | 경로 1과의 관계(K-9 뒤) |
|---|---|---|
| 1 | UNRECOVERABLE·BLOCKED LOC에도 $n_S$를 계산해 넣는다($n_P$·dP는 null). K-8이 "모든 R4 평가 LOC"에 걸리기 때문이다 | 경로 1도 같은 값을 넣음 |
| 2 | LOC 식별: decisions 행은 `r4_due_without_gate` 참인 decision 주기를 R4 LOC 집합으로 쓰고 사건과 대조한다(K-6). 옛 제어기 행은 다른 기록이 없어 3.1절 정의대로 사건을 쓰고, (b)/(c)는 `soil.t_loc_s` 주기와 비교해 정한다. 대조용으로 `slope_clearance_margin.flat_soil_margin_t_s` 주기 = 적용 사건 주기도 확인했다(33행 모두 같음) | 결과 같음 |
| 3 | $t_S$ 경로 2: `mode_starts`(S-Ch), 그다음 `soil_mode_t_s`(주기 < $n_R$일 때), 그다음 사건 폴백. UNRECOVERABLE 18건은 모두 `soil_mode_t_s`가 $n_R$ 뒤라서 사건 폴백을 썼고, 일관성 조건(`soil_mode_t_s` 주기 > 폴백 주기)은 참이었다 | $n_S$ 33/33 같음 |
| 4 | `REVOKED_AFTER_R4`: 취소 사건 주기 > $n_R$ | 같은 18행 |
| 5 | NONE 이유: 토양 모드 없음, E3c10, 그 밖 순서로 처음 걸린 것. `S9SL_X6rb_rm2p86` 2행은 E3c10 사건이 있지만 "토양 모드 없음"이 된다 | 같음 |
| 6 | (case, 태그)의 case = 행 폴더 이름(`args.case` 아님) | 비교 대상 아님(기록 항목). 값은 같음 |
| 7 | 중앙값은 `statistics.median`이다. 짝수 건이면 float(PATCH −20.0) | 같음(−20.0) |
| 8 | 정규 목록 줄 = `S9/<배치>/<행>/result.json` TAB sha LF. E 목록도 사유 열 없이 만든다 | 목록 sha 같음 |
| 9 | K-3 부분 기록: `controller_meta`나 `soil`에 `error` 키가 있으면 부분 기록 | 해당 행 없음 |
| 10 | 8절 예측 안/밖 판정은 경로 2 출력에 넣지 않았다(10.2 비교 대상 밖). 이 판정서 7절은 경로 1 값에 경로 2 해석을 덧붙였다 | P-2 해석은 7절 |
| 11 | 6.2절 판정 불가 후속 선택지는 새 실행이 필요해 사용자 승인 대상이다. 등급 확정은 K-9 뒤로 미룬다 | 14절 |

## 12. 공개: 본 것의 시점

### 12.1 봉인 전에 본 데이터 (규칙 1절 그대로)

- 저장 Chrono 행 3개의 $t_P$·$t_S$를 봤다: S-Ch gateoff·gateon(A, PATCH, dP −20)과 `batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ2FL`(B, PATCH, dP −20). 이번 재집계에서도 세 행 모두 −20이다.
- 그 밖에는 300개 result.json의 메타(키 이름, settings, 태그, 유무 불리언)만 스캔했다(규칙 1.2·2.5절). $t_P$·$t_S$·$t_{LOC}$·`mode_starts`·`decisions`·사건 값은 보지 않았다.
- control-expert의 앞선 판정(FINAL-REP·RV·G6·D424 등)이 사건 이름·LOC 시각·토양 모드 유무를 본 적이 있다. LOC 취소(L1gs)가 J1 ×1.1에서 났다는 것도 그때 알았다(사전 예측 P-6 근거). $t_P$는 그 판정 항목이 아니었다.

### 12.2 봉인 뒤 판정 전에 본 것

- 경로 2 작성 중: S-Ch gateoff 1행과 FINAL-REP `P3b_J1_B_top_Fs4` 1행의 **키 구조**(키 이름·자료형, decision·`mode_starts`·사건 항목의 키 이름)만 출력해 봤다(`probe_keys.py`, 지움). 값은 출력하지 않았다.
- 그 뒤의 값은 경로 2 스크립트가 처음 계산할 때 처음 봤다. 스크립트는 그 뒤 고치지 않았다(미사용 함수 하나를 지운 것은 실행 전).

### 12.3 판정 뒤 본 것

- 13절의 사건 순서와 최종 LOC 값. 등급을 정한 뒤에 봤고, 등급에 쓰지 않는다.

## 13. 판정 뒤 참고 분석 (등급과 무관, 결과를 본 뒤 읽은 기록)

- 도구: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\k1adopt_p2\posthoc_final_loc.py` → `posthoc_final_loc.json`. A의 UNRECOVERABLE 18행과 `B_SOFT_NONPOS` 3행에서 LOC·토양 모드·취소 사건 주기와 최종 LOC 메타를 읽는다.
- 사실 (21행 모두 같은 꼴)
  1. 사건 순서: 토양 모드 시작(주기 330~375), LOC와 R4 적용(A행. 같은 주기), LOC 취소(LOC 뒤 3~15주기), **토양 모드 재시작(취소 다음 주기)**, 두 번째 LOC(재시작 뒤 7~21주기).
  2. 두 번째 LOC의 `soil.t_P_s`는 재시작한 `soil_mode_t_s`와 **같은 float**다(21/21). 그래서 최종 LOC 그림자 dP는 21행 모두 **0**이다.
  3. A행 두 번째 LOC에는 R4 사건이 없다. 관문 꺼짐 실행에서 R4c30 틈 목표는 첫 LOC에서 정해진 뒤 취소를 지나서도 유지되고, 다시 평가되지 않았다(`flat_soil_margin_t_s` 1건).
- 해석(추정, 코드로 확인하지 않음)
  - 취소 뒤 토양 모드가 다시 시작되는 주기와 S-1 평탄 창 꼬리의 첫 표본이 같은 표본에서 정해지는 것으로 보인다(LOC 창 재시작 LWa, 또는 취소 때 창을 비우는 처리). 그렇다면 **취소 뒤 두 번째 LOC의 dP = 0은 토양 성질이 아니라 구조적 결과**다.
  - K1이 켜진 실행에서 이 구조가 문제가 되는 경로는 하나다. 첫 R4 LOC에서 K1이 막고(dP ≤ 0) → 취소 → 두 번째 LOC에서 R4를 다시 평가하는 경우다(규칙 12절 "그림자의 범위"). 이때 두 번째 LOC는 dP = 0이라 다시 막힌다. 반대로 첫 LOC에서 dP > 0이면 K1은 R4c30을 허용하고, 틈 목표는 관문 꺼짐 실행처럼 취소 뒤에도 남을 것이다.
  - 그래서 18건의 결론은 **첫 R4 LOC의 dP 한 값**에 달려 있다. 저장 결과는 그 값을 담고 있지 않다.

## 14. 판정 불가의 후속 선택지 (사용자 결정 사항)

- 규칙 6.2절: "전환하지 않는다. 건수·행을 공개한다. 선택지(예: 관문 꺼짐 + decisions 기록 재실행)는 사용자에게 묻는다. 새 실행은 사용자 승인 뒤에만 한다."
- 지금 상태: 프리셋은 K1 꺼짐 그대로(`final_C4G2_LAS`·`final_C4G2_P3_LAS`·`ABL_LAS`)다. 9절 전환 절차는 시작하지 않는다.

### 14.1 선택지 A — 관문 꺼짐 + decisions 기록 Chrono 재실행 (규칙 6.2 예시)

- 내용: 지금 코드(`order_gate.decisions`는 관문 꺼짐에서도 R4 조건 참인 LOC마다 기록된다. S-Ch gateoff가 근거)로 UNRECOVERABLE 조건을 다시 돌린다. 각 R4 LOC의 dP를 바로 읽는다. 새 봉인 규칙(이 규칙의 rev1 또는 새 규칙)이 필요하다. 대상 집합 A가 2.6절로 고정돼 있기 때문이다.
- 대상(제안, 고유 조건 7종에서 고름. 모두 패드 B, F_s 4)
  1. `P3b_J2_B_top_Fs4`
  2. `P3b_J2_B_middle_Fs4`
  3. `P3b_J2_B_bottom_Fs4`
  4. `P3b_J2_B_top_Fs4_m1p1`(×1.1)
  5. `P3b_J2_B_top_Fs4_m1p1_t180`(×1.1, 시드 20261026)
  6. `P3b_J1_B_top_Fs4_m1p1`(×1.1)
  - 제어기는 **채택 대상 프리셋(LAS-b 켬, `final_C4G2_LAS` 또는 VB `final_C4G2_P3_LAS`) + `--k1-order-gate off`**다. 규칙 12절 한계(MUST 후보가 모두 LAS-b 전 제어기)도 함께 줄인다. LAS-b 때문에 궤적이 달라져 취소가 안 날 수도 있다. 그러면 그 행은 LOC 1개짜리 (a) 출처가 되어 오히려 셀 수 있다.
  - 선택: 같은 6키의 관문 켬 짝(gateon)을 더하면 "막힘 → 취소 → 재평가" 경로(13절)를 직접 본다.
- 비용(가정: S-Ch 실측 행당 약 5,650 s, 4스레드, P 풀에 4행 동시)
  - gateoff 6행: 2묶음, 약 **3.2 h**
  - gateon 짝까지 12행: 3묶음, 약 **4.7 h**
  - 규칙 작성·감사·판정에 1~2 h를 더한다. compute-scheduler-expert 배치표와 long-running-task-monitor 점검이 필요하다(15분 넘는 작업).
- 기대: 하네스(진짜 연약 지면 dP ≥ +31)와 셀 수 있는 Chrono 13건(+49~+209)으로 보면 첫 LOC dP > 0일 가능성이 높다. 다만 18건은 J2·×1.1 쪽에 몰려 있어 13건과 조건이 다르다(3.2절). **예측하지 않고 재야 할 값이다.**
- **권고: K1 채택을 계속 원하면 이 선택지(gateoff 6행 + 선택 gateon 짝)를 1순위로 권한다.** 저장 결과로는 결론을 낼 수 없는 지점을 직접 재는 유일한 길이다.

### 14.2 선택지 B — 하네스 그림자 기록으로 대신 보기

- 내용: 하네스(K1 원판 Y 묶음 드라이버)에서 J2·×1.1 키를 관문 꺼짐 + decisions 기록으로 돌린다. 첫 R4 LOC의 dP와 취소 여부를 본다.
- 비용: 수 분~수십 분(하네스 줄 수에 따라), Chrono 없음.
- 한계
  - S-Ch에서 하네스와 Chrono의 dP가 약 12주기 어긋났다(패치 −4~−8 대 −20).
  - 하네스가 Chrono의 취소(L1gs) 패턴을 재현하는지 모른다. 하네스 "진짜 연약 지면" 근거(dP ≥ +31)는 이미 K1 원판 판정에 있다.
  - 규칙 6.2절은 Chrono 결과의 복원 불가를 다른 모델로 메우는 길을 정하지 않았다.
- 권고: **채택 근거로는 권하지 않는다.** 선택지 A의 대상 키를 고르는 사전 점검(취소가 나는 키, 대략의 dP)으로만 쓸 만하다.

### 14.3 선택지 C — 채택 보류 (K1 꺼짐 유지)

- 내용: 프리셋을 그대로 둔다. K1은 코드에 남고 기본 꺼짐이다. 판정 불가를 결정 기록에 남긴다.
- 비용: 0
- 결과
  - 패치 키(S-Ch형)에서 R4c30 +30 mm 행정이 그대로 남는다. S-Ch에서 최대 행정은 +29.9 mm, 끝 크롤러 틈은 +30 mm였다. 판정 힘과 READY는 같았다.
  - LAS-b 경계 키 C-S +30 mm 문제는 K1 원판의 동기였고, 해소되지 않은 채 남는다(알려진 한계).
  - 지금 제어기의 검증 상태는 바뀌지 않는다.
- 권고: 당장 쓸 수 있는 안전한 기본값이다. 선택지 A를 고르지 않으면 C다.

### 14.4 `B_SOFT_NONPOS` 3행(dP = 0)이 채택 판단에 주는 뜻

- 세 행 모두 **옛 제어기**(R4c30 없음, 10-30 전후)이고 **LOC 취소 뒤 두 번째 LOC**다. 13절과 같은 구조라 dP = 0이 구조적으로 나온 값으로 보인다.
- 그래서 이 3행은 "균일 연약 지면의 첫 R4 LOC에서 K1이 R4c30을 막는다"는 증거가 아니다. 지금 제어기에서 R4는 첫 LOC에서 평가되고, 그 dP는 저장되지 않았다(3.2절과 같은 공백).
- 그러나 다음 경로를 **실제로 있을 수 있는 경로**로 보여 준다. K1이 첫 LOC를 막는 경우(패치 키는 의도대로, MUST 키는 첫 LOC dP ≤ 0일 때) 취소 뒤 재평가 LOC는 dP = 0이 되어 다시 막힌다. 패치 키에서는 K1의 의도와 맞는 결과다. MUST 키에서 첫 LOC가 막히면 R4c30은 끝까지 켜지지 않는다.
- 판단: 선택지 A의 판정 규칙을 새로 쓸 때 두 가지를 정해야 한다.
  1. "R4 평가 LOC"를 첫 R4 LOC로 볼지, 모든 R4 LOC로 볼지
  2. 취소 뒤 재평가 LOC의 dP = 0을 어떻게 셀지(구조적 0을 MUST 실패로 셀지)
  - 이 구조가 코드에서 확정되면(c2.py LOC 창 재시작·취소 처리 확인), K1 정의를 보완하는 안도 후보가 된다. 예: 재평가 LOC에서는 취소 전 토양 모드 시작을 쓰거나 첫 LOC 결정을 유지한다. 이는 K1 정의 변경이라 K1 원판·Y 묶음부터 다시 해야 한다. **지금은 권하지 않고 선택지 A 결과를 본 뒤 판단한다.**

### 14.6 사용자 결정(2026-11-09 23시경)

- **A 선택**: 관문 꺼짐(`--k1-order-gate off`) + decisions 기록 Chrono 재측정으로 채택을 다시 판정한다. LAS-b 켬 프리셋, 대상 J2 상단·중단·하단·J2 ×1.1·J2 ×1.1 t180·J1 ×1.1 6키.
- 세부: gateon 짝 1~2키(J2 상단, J2 ×1.1) 포함, 하네스 사전 점검 먼저(새 규칙의 "봉인 전에 본 것"으로 공개하고 채택 근거로 쓰지 않는다), "취소 뒤 재평가 LOC" 처리를 새 봉인 규칙에 미리 정의(D-5).
- 순서: 새 봉인 규칙 → 실행 전 감사 → 실행. 이 판정(판정 불가)은 바뀌지 않는다.

### 14.5 사용자에게 물었던 결정

| # | 질문 | 선택지 | 권고 |
|---|---|---|---|
| D-1 | K1 조건부 채택을 계속 추진하는가 | (가) 선택지 A로 Chrono 재측정 / (나) 선택지 C로 보류 | 채택이 여전히 필요하면 (가), 아니면 (나). 둘 다 지금 제어기의 검증 상태는 바꾸지 않는다 |
| D-2 | (가)라면 범위 | gateoff 6행(약 3.2 h) / gateoff 6 + gateon 6(약 4.7 h) | gateoff 6 + gateon 짝 1~2키(J2 상단, J2 ×1.1)로 막힘 → 취소 → 재평가 경로를 한 번은 본다 |
| D-3 | (가)라면 제어기 | 채택 대상(LAS-b 켬) / 저장 행과 같은 옛 프리셋(재현) | 채택 대상(LAS-b 켬). 규칙 12절 한계를 함께 줄인다 |
| D-4 | 하네스 사전 점검(선택지 B) | 한다(대상 키 선정용) / 안 한다 | 하면 좋지만 필수는 아니다 |
| D-5 | `B_SOFT_NONPOS` 처리 | 기록만 / 다음 규칙에서 재평가 LOC 정의에 반영 | 다음 규칙에서 "취소 뒤 재평가 LOC" 처리를 미리 정한다(14.4) |

## 15. 한계와 교훈

- 규칙 12절의 한계(제어기 차이, 그림자의 범위, 막힘 효과 미관측, A 구성)는 그대로다. 이번 결과로 "그림자의 범위" 한계가 실제 공백(18건)이 되었다.
- 셀 수 있는 13건은 J1 ×1.0이 대부분이다. J2 ×1.0 OK는 1건(`sgRRd150`), ×1.1 OK도 1건(seed20261029)뿐이다. 13건의 큰 여유(+49 이상)가 J2·×1.1 첫 LOC에서도 성립한다고 말할 수 없다.
- 교훈(규칙 작성): 마지막 값만 남는 메타 필드(`soil.t_P_s`)에 기대는 그림자 판정을 봉인하기 전에, 그 필드를 덮어쓰는 사건(`INFO_LOC_REVOKED`)의 건수를 값을 보지 않고 먼저 셌어야 했다. 사건 이름 건수만으로 18건 공백을 봉인 전에 알 수 있었다.

## 16. 파일

| 파일 | 역할 | sha256 |
|---|---|---|
| `06_analysis/03_hydraulic/coupled/v5/las/k1/judge_adopt.json` | 경로 1 공식 판정 JSON | `da8aaeeb…3812` |
| `06_analysis/03_hydraulic/coupled/v5/las/k1/adopt_list.json` | 경로 1 목록 | `7abc0485…cc6b` |
| `…\scratchpad\k1adopt_p2\recount_adopt.py` | 경로 2 도구 | `bcec7929…7d8a` |
| `…\scratchpad\k1adopt_p2\recount_adopt.json` | 경로 2 출력 | `ded4a30e…2d5` |
| `…\scratchpad\k1adopt_p2\k9_compare.py` / `k9_compare.json` | K-9 대조 | (로컬 기록) |
| `…\scratchpad\k1adopt_p2\posthoc_final_loc.py` / `posthoc_final_loc.json` | 13절 참고 분석 | (로컬 기록) |
| `…\scratchpad\k1adopt_p2\show.py` | 경로 2 자기 출력 요약 보기(22:30:38, 판정에 쓰지 않음) | (로컬 기록) |
| `…\scratchpad\k1adopt_p2\p1_keys.py` | K-9 직전 경로 1 출력 키 구조 확인(22:33:21, 지움) | — |

- scratchpad 경로 접두는 `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\`다.
