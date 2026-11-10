# LAS-b K1 조건부 채택 재측정 판정서 (`V5-LAS-K1-REM`, Chrono SCM 관문 꺼짐/켬 직접 측정)

- 작성: control-expert, 2026-11-10
- 상태: **판정 후 감사 반영판(차단 0).** verif-protocol-auditor `[시점] 판정 후` 감사 뒤 문구만 고쳤다(HEAD 시점 서술, judge 명령 인자, K-10 맞춤·어댑터 공개, PAIR_DIVERGE 미확정, 감사 저장본 성격, 감사 저장 시각, 전환 근거 인용). 등급과 수치는 그대로다. 커밋은 메인 세션이 한다.
- 규칙: `las_k1_rules_adopt2.md`(새 원판, sha256 `fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8`). 개정판 없음.
- **최종 판정: `통과`**(4.2절 마지막 줄. 조건 ①·②·③ 참, K-0~K-10 모두 참).
  - 판정 도구 잠정 등급 `통과`(`grade_code` `pass`, 종료 0)와 경로 2 잠정 등급 `통과`가 같고, K-10 대조(11절)는 522항목 불일치 0이다.
  - 관문 꺼짐 6행(R1~R6) 모두 `POS`다. $L_1$ dP는 +99 ~ +206주기이고 `THIN_MARGIN`(≤ 12)은 0건이다.
  - 관문 켬 짝 R7·R8은 $L_1$에서 R4c30을 적용했고, 명령이 짝 gateoff와 비트 단위로 같다.
- **K1 채택 조건**(규칙 4.2 `통과` 행: "adopt 9절 전환 절차의 승인 조건 충족") **을 충족한다.** 착수는 메인 세션이 사용자에게 알리고 승인을 받은 뒤 한다(2026-11-08 저녁 방침, 13절).
- **알려진 한계(규칙 4.2 의무 문구)**: F2(정보용)가 `FORCED_R4_NEVER`다. **K1이 첫 R4 LOC를 막으면 R4c30이 끝까지 없다는 경로가 Chrono에서 확인됐다**(6절). 판정 행에서는 $L_1$ dP > 0이라 이 경로가 **관측되지 않았다**(3.3절).
- 사전 예측 11항목 중 9항목이 안이다. **P-2(R4↔R5 $n_{loc}$ 차 35 > 20)와 P-5(취소 행 3 < 4)가 밖**이다. 예측은 판정 기준이 아니다(규칙 8절). 공개와 해석은 7절에 있다.
- 규약
  - 제어: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 다리 행정 속도 명령 [m/s]).
  - 시각은 Chrono 절대 시각 [s]이다(8 s 정착 포함, 폐루프 120 s). 비교는 $n = \mathrm{round}(t/0.1)$ 정수 주기로 한다. 짝 일치(K-7)만 같은 float인지를 본다.
  - 행정은 모터 행정 [m]이고 표에서는 mm로 적는다. 크롤러 틈은 끝 시점 P3b 격자 최소 틈 [m]이다.
  - 이름: 이 판정서의 K1은 LAS-b K1(R4c30 순서 관문, `flat_soil_margin_order_gate`)이다. 2026-11-05에 탈락한 touch-phase K1과도, 하네스 키 토큰 `K1`(크롤러 강성 ×1)과도 다르다.

| 기호 | 뜻 | 단위 |
|---|---|---|
| LOC | 크롤러 이탈 확정(`crawler_liftoff_confirmed`) | — |
| decision | `controller_meta.slope_clearance_margin.order_gate.decisions[i]` | — |
| $L_1$ | 행의 첫 R4 평가 LOC(`r4_due_without_gate` 참인 첫 decision) | — |
| $t_P$, $n_P$ | 이번 LOC를 확정한 S-1 평탄 창 꼬리 첫 표본 시각, 그 주기 | s, 주기 |
| $t_S$, $n_S$ | LOC 앞 마지막 토양 모드 시작 시각, 그 주기 | s, 주기 |
| dP | $n_P - n_S$. K1은 dP ≤ 0이면 R4c30을 막는다 | 주기 |
| $n_{r}$ | LOC 취소 주기(`INFO_LOC_REVOKED`) | 주기 |
| `struct_zero` | 취소 뒤 LOC이고 $n_S$ = 취소 뒤 첫 토양 모드 재시작 주기이고 $n_P = n_S$ | — |
| $s_{max}$ | 네 다리 모터 행정 최대 | m |

## 0. 규칙·실행 정체성·파일

### 0.1 규칙·감사

| 파일 | sha256 | 시각(+09:00) |
|---|---|---|
| 규칙 원판 `las_k1_rules_adopt2.md` | `fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8` | 봉인 2026-11-09 23:03:15, 커밋 `388a6ec`(23:04:02) |
| `las_k1_rules_adopt2.sha256` | `eb9c1417710a3b4bfe626ef0c6dd7c057cc6e982fef1e90a506a1801ab765679` | 같음 |
| 실행 전 감사 리포트 `06_analysis/03_hydraulic/coupled/v5/las/k1/rem_prelaunch_audit.md` | `0abe26cc2d8a3465e0da5d78e6648d453a8495c71e11103c38838daa09c2a3b1` | 감사 HEAD `c82c5b7`, prelaunch 기록 = 판정 때 파일(K-0) |
| 판정 도구 `scripts/las_k1_rem_judge.py` | `49be3d10968cac46e24d31255e2d9cad9221626076f664c9e2bfbe4bf8d6e7d5` | 감사 기록 = prelaunch = postrun = judge = 지금 파일 |

- 규칙 sha는 판정 도구(K-0)와 경로 2(`rules_sha_eq_sha256_file`, `rules_sha_eq_expected`)가 각각 다시 계산했고 모두 봉인 값과 같다.

### 0.2 실행 정체성 (10행 공통)

| 항목 | 값 | 근거 |
|---|---|---|
| 실행 HEAD | `88e2880c2bb1a98e8758fc8f6a766e8770572621`. 10행 `code_state.git_at_start.head` = prelaunch HEAD = postrun HEAD = 판정서 작성 시점(08:53:05) HEAD. 그 뒤 08:53:45에 메인 세션이 마스트 가지를 병합해 master HEAD가 `00c9770`이 됐다(postrun 08:50:32 뒤, 8절) | K-1, 경로 2 K-1(`batch_head_eq_result_head`), `git rev-parse HEAD`(작성 시점) |
| 코드 diff | prelaunch ↔ postrun: 두 HEAD가 모두 `88e2880`이고 postrun `code_diff_since_prelaunch.quiet` 참(경로 `03_src 02_params 04_scripts`). 판정서 작성 시점(HEAD `88e2880`)에 `git diff --quiet 88e2880 HEAD -- 03_src 02_params 04_scripts`를 다시 실행해 종료 0이었다. `88e2880` ↔ `00c9770`은 같은 경로에서 **참이 아니다**: 바뀐 코드 파일은 `04_scripts/01_dynamics/run_mast_flex_c2_check.py`, `04_scripts/03_control/r8d1/mast_flex_r8c2.py`(새 파일) 2개이고 `03_src`·`02_params`·`04_scripts/02_chrono`는 같다. 두 파일은 실행 경로 밖이다(`git grep` `00c9770 -- 03_src 04_scripts/02_chrono 06_analysis/02_control/verif_matrix/scripts` 0건). 나머지는 문서·결과 파일이다 | K-1 |
| dirty | 10행 dirty 빈 목록, batch dirty 빈 목록. prelaunch·postrun `git status --porcelain --untracked-files=no` 0줄(허용 목록 빈 목록). 판정서 작성 때도 0줄 | K-1 |
| 코드 sha | 0.2.1 표 | K-2 |
| DLL | `chrono_hull_hook.dll` `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(prelaunch = postrun = 지금) | K-3 |
| hull hook | 10행 `mode` = `requested` = `fast`, `fallback_reason` None, batch `mixed_hull_mode` 거짓, progress.log `MIXED_HULL_MODE` 0줄 | K-3 |
| threads·OMP | `args.threads` 4 = `num_threads_chrono`, batch entry `omp_wait_policy` `PASSIVE` | K-4 |
| 풀 | 계획 10행 모두 `pcore`(`rem_batch_plan.json` `fbb9c7ed…b363`), batch `parallel` 4, `parallel_e` 0, `e_cases` 빈 목록, 10행 `pool` `pcore`. 짝 세트(R1·R7·F1, R4·R8·F2) 같은 풀 | K-4, 사용자 결정 1(P만) |
| 인자 | 2.2·2.3 표와 같다. R1↔R7, R4↔R8 차이는 `--k1-order-gate` 하나, R7↔F1, R8↔F2 차이는 `--k1-forced-block first` 하나 | K-5 |
| 제어기 | VB 9행 `final_C4G2_P3_LAS`, R5 `final_C4G2_LAS`, `expect_controller.ok` 참. 판정 행 클래스 `C2Controller`, `k1_forced_block` 없음. F1·F2 `k1_forced_block.mode` `first`, `module_sha256` `f70f6786…2cc3` | K-6, F 전용 항목 |
| 종료 | 10행 `rc` 0, batch `failed` 거짓 | K-9 |

#### 0.2.1 K-2 코드 파일 (작업 트리 CRLF / HEAD blob LF)

| 파일 | 작업 트리 sha256(앞 8자) | blob sha256(앞 8자) | 결과·배치 기록 |
|---|---|---|---|
| `04_scripts/02_chrono/run_S9.py` | `cf6485f2` | `c8567240` | 기록 없음 |
| `04_scripts/02_chrono/s9_batch.py` | `84b1bb1a` | `d8b4b578` | 기록 없음 |
| `04_scripts/02_chrono/las_k1_rem_chrono_rows.py` | `aa6e1348` | `fe96fcf8` | 기록 없음 |
| `04_scripts/02_chrono/k1_forced_block.py` | `f70f6786` | `2ace7acb` | F1·F2 `module_sha256`만(같음) |
| `03_src/outrigger_sim/control/c2.py` | `a75d2780` | `254921d1` | result.json·batch.json 기록 같음 |
| `03_src/outrigger_sim/control/zero_calibration.py` | `b63a7a47` | `e55d3dd6` | result.json·batch.json 기록 같음 |
| `03_src/outrigger_sim/chrono/hull_hook.py` | `afef13ec` | `aae84958` | 기록 없음 |
| `04_scripts/03_control/s9/late_loc_rule.py` | `76b54910` | `76b54910`(LF 파일) | 기록 없음 |
| `03_src/outrigger_sim/hydraulics/v5_options.py` | `66d92410` | `3097c670` | 기록 없음 |

- **K-2 기재 의무(감사 해석 2)**: result.json·batch.json에 sha가 기록된 파일은 `c2.py`·`zero_calibration.py` 둘뿐이다. **나머지 7개 파일(`run_S9.py`, `s9_batch.py`, `las_k1_rem_chrono_rows.py`, `k1_forced_block.py`, `hull_hook.py`, `late_loc_rule.py`, `v5_options.py`)은 기록 sha가 없어 prelaunch·postrun·HEAD로 대조했다.** 셋 다 같다. 판정서 작성 시점(HEAD `88e2880`, 8절)에 control-expert가 작업 트리 원시 바이트와 `git show HEAD:<경로>` 원시 바이트를 다시 해시해 prelaunch·postrun 값과 같음을 확인했다(`blob_check.py`, 11.3절). `k1_forced_block.py`는 F1·F2 `module_sha256` 기록과도 같다.
- 남는 틈(감사 해석 2 그대로): 실행 중 편집했다가 되돌린 경우는 이 대조로 잡지 못한다. `hull_hook.py`, `v5_options.py`, `late_loc_rule.py`, `s9_batch.py`, 행 모듈은 행 dirty 경로 밖이다.
- `c2.py` blob `254921d1…a1de`이 `859deef`의 blob과 같다(prelaunch `c2_blob_is_base` 참, 판정서 작성 때 `git show 859deef:` 재해시로 다시 확인). 변형이 `c2.py`를 바꾸지 않았다.

### 0.3 결과 파일 (로컬 전용)

배치 폴더: `07_results/S9/batch_V5-LAS-K1-REM_20261109_235554`

| 파일 | sha256 |
|---|---|
| `batch.json` | `35a1d613125d642f27bd6435bae10735958f5a7aa13f87b24f81f600006007d8` |
| `progress.log` | `5bbfb42aaa4ebdbb19d681fd55d01fdc0d26217d073901cdc9d63efff7cfd82d` |
| R1 `REM_J2_B_top_Fs4_VB_gateoff/result.json` | `3bb27cd308e0f507397bc5aad051d5a9657177be5d92a18c834d1b945c4cc0db` |
| R2 `REM_J2_B_middle_Fs4_VB_gateoff/result.json` | `42aafc5028881ba68b589c86d0fb7f26469ff81b119318ce740a4dac6023b44c` |
| R3 `REM_J2_B_bottom_Fs4_VB_gateoff/result.json` | `0c9fda1550fe0a6d87d857b76ea4687132809ac989252f9812ca07483a7599e4` |
| R4 `REM_J2_B_top_Fs4_m1p1_VB_gateoff/result.json` | `2f5cb250b2319544612c91a6d30e2ee405b798ef526e0e7b71856b0aa02439b2` |
| R5 `REM_J2_B_top_Fs4_m1p1_V0_gateoff/result.json` | `8f6e8ac6573fbe851081fe41fc89db0fd87cafd67ee68b3fc557e378ce8e2518` |
| R6 `REM_J1_B_top_Fs4_m1p1_VB_gateoff/result.json` | `50f8c400f619061b683f71617f53a9964fdd9c72405249a1582ac3dbb206e0af` |
| R7 `REM_J2_B_top_Fs4_VB_gateon/result.json` | `a237b50b22176018e3db995209bc9b55780445855999412621a4d7c2788ddc5a` |
| R8 `REM_J2_B_top_Fs4_m1p1_VB_gateon/result.json` | `fd5c22f4942c7254cc953a235ddd03affcb169618cf03a8d0f170685a08faccf` |
| F1 `REM_J2_B_top_Fs4_VB_gateon_forced1/result.json` | `bac8a552c29f24bb913aff6867b48686ece5bdb55e33ba54a28497ad3d728e8e` |
| F2 `REM_J2_B_top_Fs4_m1p1_VB_gateon_forced1/result.json` | `3151d96803df5f1d0a101401f5f89f82673478c082358dd3b7f09cc1c2b1f917` |
| R1·R7 `controller_commands.npz` | 둘 다 `ebf86d1d40af464e2e4e23d4ea79ad56721829e65d70cb4efb1d2cc072e4b559` |
| R4·R8 `controller_commands.npz` | 둘 다 `97aace614a534a6aa95f67857947dcd541f9ecca1e9974eb5105fc017bf7c8aa` |
| `06_analysis/03_hydraulic/coupled/v5/las/k1/rem_prelaunch.json` | `1714f8837f144019888ad3825644bc1d23d4053b1080d56b5584df72f81d970c` |
| `…/k1/rem_postrun.json` | `2c8fd7b2ab42697314900d77ea97ac59d33c6329d102f7a7f115021f62fa34ee` |
| `…/k1/judge_REM.json`(경로 1, 공식 판정 JSON) | `f27594512696aaefab3ae3bcc5c5a3ea7688a9b3618937c4ac47927c418afc9e` |
| 경로 2 `…\scratchpad\k1rem_path2\path2_REM.json` | `5ecde300426afbb7b30a33931ae315a305a0fb7962024ea79a1cf9e83de1785f` |

- 두 경로가 함께 읽은 입력 16개(batch.json, result.json 10개, 명령 npz 4개, 규칙)의 sha256은 두 출력의 `files_read_sha256`에서 모두 같다(K-10 `files_read` 16/16).
- 공식 판정 명령: `las_k1_rem_judge.py judge --batch <배치 폴더> --expect-tool-sha 49be3d10…`(dynamics-dev, 메인 세션 실행). 실제로 준 인자는 `--batch`와 `--expect-tool-sha` 둘뿐이다. `--prelaunch`·`--postrun`·`--rules`·`--out`은 주지 않았고, 도구 기본 경로가 위 표의 같은 파일(`rem_prelaunch.json`, `rem_postrun.json`, `las_k1_rules_adopt2.md`, `judge_REM.json`)을 읽고 썼다. `judge_REM.json` `files_read_sha256`의 경로·sha가 위 표와 같다. `status` `pass`, 종료 0, `provisional` 참, `k10` null.
- 실행 시간(batch.json `wall_s`): ×1.1 4행 6,083~6,668 s, J2 상단 ×1.0 3행 6,230~6,560 s, J2 중·하단 4,795 / 4,825 s. 직렬 합 61,141 s(계획 추정 49,500 s의 1.24배), 벽시계 23:55:54~04:47:41(4 h 51 min 47 s).

## 1. 정체성·일관성 K-0~K-10 (판정 행 R1~R8)

| # | 결과 | 비고 |
|---|---|---|
| K-0 | 참 | 규칙 sha = `.sha256` 기록. 도구 sha 감사 기록 = prelaunch = postrun = judge = 지금 파일(`49be3d10…`). 감사 리포트 sha prelaunch = 지금(`0abe26cc…`) |
| K-1 | 참 | 0.2절 |
| K-2 | 참 | 0.2.1절(기재 의무 문장 포함) |
| K-3 | 참 | 0.2절 |
| K-4 | 참 | 0.2절. 10행 `pcore`, 짝 세트 같은 풀 |
| K-5 | 참 | 0.2절 |
| K-6 | 참 | 관문 꺼짐 6행: R4 평가 decision 각 1건(≤ 1), `SKIPPED:order` 사건 0. keep 설정 참, `max_revokes` 2, `period_s` 0.1, `decisions` 키 존재 |
| K-7 | 참 | 3.1절. **`ok: None` 경우는 없었다**(R7·R8 모두 `NO_R4`가 아니고 $L_1$ 튜플이 float까지 같다) |
| K-8 | 참 | (a)~(f) 모두 참. 토양 모드 전 LOC 0건(사용자 결정 4의 stop 조건은 생기지 않았다) |
| K-9 | 참 | `MISSING` 0행, 불일치 0 |
| K-10 | 참 | 11절. 522항목 불일치 0 |

- F1·F2 전용 항목(K-1~K-5, `k1_forced_block.mode` `first`, `class`·`module_sha256`, `c2_setup.k1_forced_block` `first`, 관문 `enabled` 참, 강제 호출 정확히 1건): 두 행 모두 참. 두 변형 모두 `valid` 참.

## 2. 행별 결과

### 2.1 상태와 $L_1$ (관문 꺼짐 6행 + 짝·변형)

| 행 | case | 상태 | $n_{loc}$ | $t_P$ [s] | $t_S$ [s] | $n_P$ | $n_S$ | **dP** | $n_{loc}-n_P$ | `applied` | 취소 $n_r$ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | J2 상단 ×1.0 VB off | `POS` | 468 | 45.1 | 35.2 | 451 | 352 | **+99** | 17 | 참 | 없음 |
| R2 | J2 중단 ×1.0 VB off | `POS` | 468 | 45.1 | 35.1 | 451 | 351 | **+100** | 17 | 참 | 없음 |
| R3 | J2 하단 ×1.0 VB off | `POS` | 468 | 45.1 | 35.1 | 451 | 351 | **+100** | 17 | 참 | 없음 |
| R4 | J2 상단 ×1.1 VB off | `POS` | 588 | 57.3 | 37.5 | 573 | 375 | **+198** | 15 | 참 | 599 |
| R5 | J2 상단 ×1.1 **V0** off | `POS` | 553 | 53.9 | 33.3 | 539 | 333 | **+206** | 14 | 참 | 566 |
| R6 | J1 상단 ×1.1 VB off | `POS` | 514 | 49.9 | 35.1 | 499 | 351 | **+148** | 15 | 참 | 520 |
| R7 | J2 상단 ×1.0 VB **on** | `POS` | 468 | 45.1 | 35.2 | 451 | 352 | +99 | 17 | 참 | 없음 |
| R8 | J2 상단 ×1.1 VB **on** | `POS` | 588 | 57.3 | 37.5 | 573 | 375 | +198 | 15 | 참 | 599 |
| F1 | R7 + 강제 막힘(정보용) | (`POS`) | 468 | 45.1 | 35.2 | 451 | 352 | +99 | 17 | **거짓**(강제) | 없음 |
| F2 | R8 + 강제 막힘(정보용) | (`POS`) | 588 | 57.3 | 37.5 | 573 | 375 | +198 | 15 | **거짓**(강제) | 601 |

- 10행 모두 $L_1$이 행의 첫 LOC이고 `post_revoke` 거짓이다. `LATE_R4` 0, `NONPOS` 0, `LATE_STRUCT` 0, `NO_R4` 0, `MISSING` 0.
- 10행 모두 decision의 기록 주기($n_P$, $n_S$, dP)가 재계산과 같다(`recorded_periods_match` 참).
- 10행 모두 E3c10 LOC 0건이다.
- 토양 모드 시작은 모두 `source` `release`다: R1·R7·F1 352, R2·R3 351, R4·R8 375·600, R5 333·567, R6 351·521, F2 375·602(주기).

### 2.2 decision 표 (전부)

| 행 | i | $n_{loc}$ | $n_P$ | $n_S$ | dP | r4_due | would_block | applied | post_revoke | restart_n | struct_zero |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | 0 | 468 | 451 | 352 | 99 | 참 | 거짓 | 참 | 거짓 | — | 거짓 |
| R2 | 0 | 468 | 451 | 351 | 100 | 참 | 거짓 | 참 | 거짓 | — | 거짓 |
| R3 | 0 | 468 | 451 | 351 | 100 | 참 | 거짓 | 참 | 거짓 | — | 거짓 |
| R4 | 0 | 588 | 573 | 375 | 198 | 참 | 거짓 | 참 | 거짓 | — | 거짓 |
| R4 | 1 | 607 | 600 | 600 | 0 | 거짓 | 거짓 | 거짓 | 참(599) | 600 | **참** |
| R5 | 0 | 553 | 539 | 333 | 206 | 참 | 거짓 | 참 | 거짓 | — | 거짓 |
| R5 | 1 | 574 | 567 | 567 | 0 | 거짓 | 거짓 | 거짓 | 참(566) | 567 | **참** |
| R6 | 0 | 514 | 499 | 351 | 148 | 참 | 거짓 | 참 | 거짓 | — | 거짓 |
| R6 | 1 | 530 | 521 | 521 | 0 | 거짓 | 거짓 | 거짓 | 참(520) | 521 | **참** |
| R7 | 0 | 468 | 451 | 352 | 99 | 참 | 거짓 | 참 | 거짓 | — | 거짓 |
| R8 | 0 | 588 | 573 | 375 | 198 | 참 | 거짓 | 참 | 거짓 | — | 거짓 |
| R8 | 1 | 607 | 600 | 600 | 0 | 거짓 | 거짓 | 거짓 | 참(599) | 600 | **참** |
| F1 | 0 | 468 | 451 | 352 | 99 | 참 | **참**(강제) | 거짓 | 거짓 | — | 거짓 |
| F2 | 0 | 588 | 573 | 375 | 198 | 참 | **참**(강제) | 거짓 | 거짓 | — | 거짓 |
| F2 | 1 | 610 | 602 | 602 | 0 | **참** | **참**(원래 규칙) | 거짓 | 참(601) | 602 | **참** |

- 관문 꺼짐·켬 행의 취소 뒤 decision(R4·R5·R6·R8 i = 1)은 `r4_due_without_gate` 거짓이다. $L_1$에서 적용된 +30 mm 목표가 keep으로 남아(규칙 1.2절) R4가 다시 평가되지 않았다. 규칙 3.3 #1의 가정(관문 꺼짐 행의 R4 평가 decision ≤ 1)이 성립한다.
- F2 i = 1은 $L_1$이 막혀 목표가 없으므로 R4가 다시 평가된 경우다(규칙 1.2절 `_revoke_loc`). 6절.

### 2.3 행 끝 기록 (등급과 무관)

| 행 | $s_{max}$ [mm] | 끝 크롤러 틈(격자) [mm] | 첫 DONE [s] | 첫 READY [s] | 마지막 phase | FAULT_·WARN_ |
|---|---|---|---|---|---|---|
| R1 | 533.22 | 63.22 | 57.2 | 81.9 | `ready` | 없음 |
| R2 | 532.91 | 67.13 | 58.2 | 87.5 | `ready` | 없음 |
| R3 | 540.51 | 69.23 | 65.3 | 77.3 | `ready` | 없음 |
| R4 | 615.38 | 66.71 | 71.2 | 117.6 | `ready` | 없음 |
| R5 | 622.85 | 71.87 | 83.1 | 106.9 | `ready` | 없음 |
| R6 | 605.29 | 58.57 | 64.6 | 113.6 | `ready` | 없음 |
| R7 | 533.22 | 63.22 | 57.2 | 81.9 | `ready` | 없음 |
| R8 | 615.38 | 66.71 | 71.2 | 117.6 | `ready` | 없음 |
| F1 | 501.86 | 35.69 | 69.5 | 81.5 | `ready` | 없음 |
| F2 | 584.52 | 35.54 | 72.7 | 115.1 | `ready` | 없음 |

- 10행 모두 120 s 폐루프 안에 READY로 끝났다. FAULT·WARN 사건은 0건이다.
- 기록: R4·R8 첫 READY 117.6 s, R6 113.6 s는 P3-6 한계(100 s)를 넘는다. 이 규칙은 READY 시각을 판정하지 않는다(K1 판정 대상 아님). ×1.1 질량은 CLAUDE.md "알려진 한계"의 운용 중량 +10 % READY 103.3 s와 같은 쪽이다.

## 3. 관문 켬 짝 (조건 ③, K-7, P-8)

### 3.1 $L_1$ 튜플 (K-7, float 비교)

| 짝 | ($n_{loc}$, $n_P$, $n_S$, dP, `t_P_s`, `t_S_s`) gateoff | gateon | K-7 |
|---|---|---|---|
| R1 ↔ R7 | (468, 451, 352, 99, 45.10000000037363, 35.20000000004499) | 같음 | 참 |
| R4 ↔ R8 | (588, 573, 375, 198, 57.30000000077863, 37.50000000012134) | 같음 | 참 |

### 3.2 조건 ③과 경로

| 짝 | 짝 gateoff 상태 | gateon $L_1$ `applied` | 같은 주기 `INFO_LOC_FLAT_SOIL_MARGIN:` | 뒤 R4 평가 / `SKIPPED:order` | 경로(`GATEON_PATH`) | ③ |
|---|---|---|---|---|---|---|
| R7 | R1 `POS` | 참(468) | 있음 | 0 / 0 | $L_1$ 적용 | 참 |
| R8 | R4 `POS` | 참(588) | 있음 | 0 / 0 | $L_1$ 적용 | 참 |

- 명령: 짝끼리 `controller_commands.npz` sha256이 같다(R1·R7 `ebf86d1d…b559`, R4·R8 `97aace61…c8aa`). 경로 1의 내용 해시(`t_s`·`issued_u_m_s` 배열)도 짝끼리 같다(R1·R7 `cd7c7e7f…c21a`, R4·R8 `2628f024…3fc4`). `PAIR_DIVERGE` 0건.
- 결과 파일 비교: R7의 result.json sha는 R1과 다르지만(`a237b50b…` 대 `3bb27cd3…`), 판정에 쓰는 decision·취소·토양 모드 시작·LOC 주기·끝 기록은 모두 같다(2.1~2.3절). 다른 것으로 확인한 것은 `args`(case, `k1_order_gate`)와 관문 설정 기록이다. result.json 전체의 바이트 차이를 항목별로 나누지는 않았다.
- **규칙 3.4 의무 문구**: 판정 행 R7·R8에서 $L_1$ dP > 0이라 **"막힘 → 취소 → 재평가" 경로는 판정 행에서 관측되지 않았다**(0건을 통과로 세지 않는다). 이 경로는 F2(정보용, 6절)와 규칙 1.2절 코드 읽기, `SHADOW_RELOC`(5절)로만 봤다.

## 4. 등급

### 4.1 조건

| 조건 | 결과 | 근거 |
|---|---|---|
| ① MUST | **참** | R1~R6 모두 `POS`(6행, ≥ 4). J2 ×1.1 쪽 R4·R5 모두 `POS`(≥ 1). `NONPOS`·`LATE_STRUCT`·`NO_R4`·`MISSING` 0 |
| ② PATCH | **참(기지 행뿐)** | 이 묶음에는 패치 행이 없다. adopt ②(S-Ch 2행, dP −20, 봉인 전 기지 행)를 그대로 쓴다. **기지 행뿐이다**(재공개) |
| ③ 짝 | **참** | 3절. R7·R8 K-7 참, 짝 gateoff `POS`이고 gateon $L_1$ 적용·사건 있음·3.3 #5 참 |

### 4.2 등급 확정

- 4.2 표를 위에서부터 본다.
  - `stop`: K-0~K-10 모두 참 → 해당 없음.
  - `미달`: R1~R6에 `NONPOS`·`LATE_STRUCT` 0 → 해당 없음.
  - `판정 불가`: `MISSING` 0, `POS` 6 ≥ 4, R4·R5 모두 `POS` → 해당 없음.
  - `부분 통과`: ③ 참 → 해당 없음.
  - **`통과`**: ①·②·③ 참.
- **확정 등급: `통과`.** 판정 도구 잠정 등급 `통과`(`grade_reasons` 빈 목록)와 경로 2 잠정 등급 `통과`(`grade_reasons` "cond1, cond2 (known rows), cond3 true")가 같고, K-10이 참이므로 잠정 표시를 뗀다.
- 판정 뒤 문턱(dP > 0, `POS` ≥ 4, `THIN_MARGIN` 12)을 바꾸지 않았다. 결과 뒤 새 판도 없다.
- F1·F2(정보용)의 결과는 등급을 바꾸지 않는다(규칙 4.2). F2가 `FORCED_R4_NEVER`이므로 머리의 의무 문구를 적었다.
- **옛 제어기 `UNRECOVERABLE` 18행 자체는 여전히 셀 수 없다**(규칙 4.2 의무 문구). 이 판정은 채택 대상 제어기(LAS-b 켬)로 같은 조건을 다시 잰 것이다.

## 5. FLAG (판정 행, 등급과 무관)

| FLAG | 건수 | 내용 |
|---|---|---|
| `THIN_MARGIN`(`POS` dP ≤ 12) | **0** | 최소 dP는 R1 +99 |
| `LATE_R4` | 0 | 6행 모두 $L_1$ = 첫 LOC |
| `SHADOW_RELOC` | **3**(`struct_zero` 3, 비율 100 %) | R4 $n_{loc}$ 607(취소 599, 재시작 600), R5 574(566, 567), R6 530(520, 521). 세 건 모두 dP 0이고 $n_P = n_S$ = 재시작 주기다. R1~R3은 취소가 없어 0건 |
| `PAIR_DIVERGE` | 0 | 3.2절 |
| `GATEON_PATH` | `R4_APPLIED_LATE`·`R4_NEVER` 0건 | R7·R8 모두 $L_1$ 적용 |
| `OLD_CTRL_SHIFT` | 8행 기록 | 아래 표 |

| 행 | $n_{loc}$ − 옛 $n_R$ | $n_S$ − 옛 $n_S$ | 옛 대응(adopt 3.2, 태그 `final_C4G2`/`final_SGS_R4`, V0) |
|---|---|---|---|
| R1·R7 | +17 | +20 | J2 상단 ×1.0: 451 / 332 |
| R2 | +17 | +19 | J2 중단 ×1.0: 451 / 332 |
| R3 | +17 | +19 | J2 하단 ×1.0: 451 / 332 |
| R4·R8 | +35 | +42 | J2 상단 ×1.1: 553 / 333 |
| R5 | **0** | **0** | J2 상단 ×1.1: 553 / 333 |
| R6 | +22 | +18 | J1 상단 ×1.1: 492 / 333 |

- 하네스 대조(기록, 규칙 6절): R1 +99 대 하네스 +92~+93, R2 +100 대 +94, R3 +100 대 +94~+95(Chrono가 5~6주기 큼). R6 +148은 J1 ×1.0 하네스 +36~+38과 비교만 한다(질량이 달라 같은 양이 아니다).
- SHADOW_RELOC 해석(규칙 3.3 #2, 등급 아님): K1이 $L_1$을 막았다면 취소 뒤 재LOC가 구조적 0으로 다시 막혔을 것이라는 그림자다. 다만 +30 mm 목표 유무로 궤적이 달라지므로 정확한 대리값이 아니다. 실제 막힌 궤적은 F2가 보였다(6절).

## 6. F1·F2 막힘 강제 진단 (정보용, 등급에 넣지 않음)

| 항목 | F1(J2 상단 ×1.0, 짝 R1) | F2(J2 상단 ×1.1, 짝 R4) |
|---|---|---|
| `valid`(F 전용 K 항목) | 참 | 참 |
| `FORCED_AT_L1`(강제 LOC = $L_1$) | 참(468) | 참(588) |
| `FORCED_PAIR_L1`($L_1$ 튜플 = 짝 R) | 참 | 참 |
| 강제 호출의 원래 규칙 값 `natural_blocked` | 거짓(dP +99) | 거짓(dP +198) |
| $L_1$ 뒤 취소 | 없음 | 601(60.1 s) |
| 재평가 decision | 없음 | $n_{loc}$ 610, $n_P = n_S$ = 602, dP 0, `struct_zero` 참, 원래 규칙으로 막힘(`applied` 거짓, `SKIPPED:order` 사건 1) |
| **경로 분류** | **`FORCED_NO_REVOKE`** | **`FORCED_R4_NEVER`** |
| `applied` 참 decision | 0 | 0 |
| $s_{max}$ / 짝 대비 | 501.86 mm / **−31.36 mm** | 584.52 mm / **−30.86 mm** |
| 끝 크롤러 틈 / 짝 대비 | 35.69 mm / −27.53 mm | 35.54 mm / −31.16 mm |
| 첫 DONE / 첫 READY | 69.5 s / 81.5 s(짝 57.2 / 81.9) | 72.7 s / 115.1 s(짝 71.2 / 117.6) |
| 마지막 phase, FAULT·WARN | `ready`, 없음 | `ready`, 없음 |

- **`FORCED_REVOKED_NO_REEVAL`(감사 해석 4의 넷째 분류)은 생기지 않았다.** F1은 취소 0, F2는 취소 1 + 재평가 1이다.
- 두 경로의 F 분류가 같다(11절). 그래서 사용자 결정 3의 "F 분류 불일치 → 정보용 무효" 처리는 쓸 일이 없었다.
- 읽는 법
  - F2는 규칙 1.2절 경로 ①이 Chrono에서 실제로 일어남을 보인다. $L_1$을 막자 취소 → 토양 모드 재시작(602) → 재LOC(610)에서 $t_P = t_S$(같은 float `60.2000000008749`)로 구조적 0 → 원래 규칙으로 다시 막힘 → 120 s 끝까지 R4c30 없음. 최대 취소 2회 중 1회만 났다.
  - F1은 강제 막힘 뒤 취소가 나지 않아 경로 ①을 보지 못했다(규칙 12절 한계 그대로).
  - 두 F 모두 +30 mm 목표가 없어 행정이 약 31 mm 작고 끝 틈이 약 28~31 mm 작다. 끝 틈은 약 35.5 mm로 남았고 READY로 끝났다.
- 판정 행에 주는 뜻: 판정 행은 6행 모두 $L_1$ dP ≥ +99라 K1이 막지 않는다. 그래서 이 경로는 채택 대상 조건(균일 연약 지면 J1·J2, 평지)에서는 일어나지 않았다. 다만 **$L_1$ dP ≤ 0인 행이 균일 연약 지면에서 생기면 R4c30이 끝까지 없을 수 있다**(채택 뒤 알려진 한계, 14절).

## 7. 사전 예측 P-1~P-11 (규칙 8절, 판정 기준 아님)

| # | 예측 | 관측 | 안/밖 |
|---|---|---|---|
| P-1 | R1·R2·R3 dP > 0, 점 ≈ +103, [+60, +140] | +99, +100, +100 | 안 |
| P-2 | R4·R5 dP > 0, 점 ≈ +204, [+120, +240]. R5 $n_{loc}$가 R4와 ±20주기 안 | dP +198, +206(안). **$n_{loc}$ 588 대 553, 차 35** | **밖** |
| P-3 | R6 dP > 0, 점 ≈ +143, [+90, +180] | +148 | 안 |
| P-4 | R1~R6 모두 `POS`, `NO_R4` 0, `LATE_STRUCT` 0 | 6/6 `POS` | 안 |
| P-5 | R1~R6 중 4~6행에서 $L_1$ 뒤 취소 ≥ 1 | **3행**(R4, R5, R6) | **밖** |
| P-6 | `SHADOW_RELOC` ≥ 70 % `struct_zero` | 3/3(100 %) | 안 |
| P-7 | R4·R5 모두 `POS`, dP 차 ≤ 30 | 둘 다 `POS`, 차 8 | 안 |
| P-8 | R7·R8 $L_1$ 적용, 명령 sha 짝과 같음, 판정 행 막힘 경로 미관측 | 그대로 | 안 |
| P-9 | `THIN_MARGIN` 0 | 0 | 안 |
| P-10 | 등급 `통과` | `통과` | 안 |
| P-11 | F `FORCED_AT_L1`·`FORCED_PAIR_L1` 참, 행정이 짝보다 작음, 취소 나면 `FORCED_R4_NEVER`, 없으면 `FORCED_NO_REVOKE` | F1 취소 없음 → `FORCED_NO_REVOKE`, F2 취소 → `FORCED_R4_NEVER`, 행정 −31.4 / −30.9 mm | 안 |

- 11항목 중 9항목이 안이다. 두 경로(판정 도구 `predictions`, 경로 2 `predictions`)의 안/밖이 11/11 같다.

### 7.1 P-2·P-5 이탈의 공개와 해석 (결과를 본 뒤 읽은 기록, 판정에 쓰지 않음)

- **사실**
  - 예측의 근거는 옛 제어기 저장 Chrono의 $n_R$·$n_S$였다(규칙 1.1절). 옛 행의 태그는 `final_C4G2`·`final_SGS_R4`이고, 모두 ③(v5 유압 VB) 없는 V0 플랜트다.
  - R5(V0 + LAS-b)는 $n_{loc}$ 553, $n_S$ 333으로 **옛 ×1.1 값과 주기까지 같다**(`OLD_CTRL_SHIFT` 0 / 0).
  - VB 행은 옛 값보다 늦다: ×1.0 +17 / +19~+20, ×1.1 R4 +35 / +42, J1 ×1.1 R6 +22 / +18.
  - 취소: 옛 제어기(V0)는 J2 ×1.0에서 R4 LOC 3주기 뒤 거의 늘 취소됐다(규칙 1.1절). 이번 J2 ×1.0 VB 3행(R1~R3)은 취소 0이다. ×1.1 3행은 모두 취소 1회다.
- **해석**
  - P-2: R4와 R5는 플랜트(VB/V0)와 태그만 다르다(규칙 2.2절). 그래서 $n_{loc}$ 차 35주기는 **VB 플랜트(③) 효과**로 본다. 예측은 VB가 LOC 시각을 옮기는 효과를 넣지 않았다. dP 자체는 둘 다 범위 안이고 차도 8주기라 K1 분류에는 영향이 없다.
  - R5가 옛 값과 같다는 것은 ×1.1·V0에서는 LAS-b가 $L_1$ 주기를 바꾸지 않았다는 뜻이다. ×1.0에서 VB 효과와 LAS-b 효과를 나눌 V0 + LAS-b 행은 이 묶음에 없다. 그래서 ×1.0의 +17주기 이동이 어느 쪽 효과인지는 **추정**으로 남긴다(같은 질량에서 R5가 0이었으므로 VB 쪽으로 본다).
  - P-5: J2 ×1.0에서 취소가 사라진 것도 같은 VB 이동(토양 모드 시작 +20주기, LOC +17주기)과 함께 나타났다. 하네스 ×1.0(1.3절)도 취소 0이었다. 원인 분해는 하지 않았다.
- **교훈**: 저장 Chrono로 주기 예측을 정할 때는 플랜트 설정(V0/VB)이 같은 행인지 먼저 맞춘다. S-Ch 판정서 4.2절 교훈(하네스 대신 저장 Chrono를 쓸 것)의 다음 단계다.

## 8. 시간 순서

| 시각(+09:00) | 사건 | 출처 |
|---|---|---|
| 11-09 23:03:15 / 23:04:02 | 규칙 봉인 / `388a6ec` | `.sha256`, git |
| 23:15:22 ~ 23:34:23 | 행 모듈·`--k1-forced-block`·변형·판정 도구 커밋과 병합(`d536f47`, `a126162`, `f484d5b`, `e993df5`, `9c68804`) | git |
| 23:34:36 | `c82c5b7`(감사 HEAD, `.gitattributes`) | git, 감사 리포트 |
| 23:42:48 ~ 23:55:06 | 문서·마스트 가지 병합(`463247a` … `88e2880`). 실행 경로 밖(감사 조건 1~3) | git |
| 23:50:02 | 실행 전 감사 저장본 `rem_prelaunch_audit.md` 저장(prelaunch 전, 10절) | 파일 시각 |
| 23:55:22 | prelaunch `pass`(HEAD `88e2880`) | `rem_prelaunch.json` `taken_utc` 14:55:22Z |
| 23:55:54 | START 4행(×1.1 묶음, P 4슬롯) | progress.log |
| 11-10 00:07:19 | 경로 2 `recount_rem.py` 고정(sha `dfe1826f…9d61`). 첫 result.json(01:37:17) 전 | 파일 시각 |
| 01:37:17 ~ 04:47:40 | 10행 END, 모두 rc 0 | progress.log |
| 04:47:41 | 배치 끝 `failed=False` | progress.log |
| 08:50:32 | postrun `pass`(차이 0) | `rem_postrun.json` `taken_utc` 23:50:32Z |
| 08:50:41 | 경로 2 출력 `path2_REM.json`(sha `5ecde300…785f`). 메인 세션이 경로 1 실행 전에 sha를 기록했다 | 파일 시각, 메인 세션 기록 |
| 08:50:55 | 경로 1 judge `pass`(잠정) | `judge_REM.json` `taken_utc` 23:50:55Z |
| 08:53:05 | 판정서 작성 시점의 HEAD 확인: `88e2880` | `git rev-parse HEAD` |
| 08:53:45 | 메인 세션이 마스트 가지 병합 → master `00c9770`(postrun 뒤) | git |

- prelaunch(23:55:22)부터 postrun(08:50:32)까지 master 커밋은 없다. `88e2880`(23:55:06) 다음 master 커밋은 `00c9770`(11-10 08:53:45)이다.
- `00c9770`은 postrun과 judge 뒤의 병합이다. 바뀐 코드 파일은 실행 경로 밖 2개(`04_scripts/01_dynamics/run_mast_flex_c2_check.py`, `04_scripts/03_control/r8d1/mast_flex_r8c2.py`)이고, 나머지는 문서·결과 파일이다. `03_src`·`02_params`·`04_scripts/02_chrono`는 바뀌지 않았다(0.2절).
- 그 병합에 들어간 `86ece90`(01:26:49)과 `5d12a2c`(01:43:10)는 실행 중 시각이지만 **worktree 가지 커밋**이다. master와 main checkout에는 08:53:45 병합으로 처음 들어왔다. 그래서 실행 HEAD와 K-1에 영향이 없다.
- prelaunch < 첫 START < 경로 2 고정 < 첫 result.json < 마지막 END < postrun < 경로 2 출력 < 경로 1 judge < 판정서 작성 시점 HEAD 확인 < `00c9770` 병합 순서가 성립한다.

## 9. 재실행·결측·감사 기재 의무

- **재실행: 없다.** progress.log `START` 10, `END` 10(모두 rc 0), `SKIP`·`RESUME` 0, `MIXED_HULL_MODE` 0. 행 폴더에 `attempt1/` 없음. `--resume`을 쓰지 않았다.
- **`rerun_of`: 없음.** 10행 모두 batch entry에 `rerun_of` 키가 없다(경로 1 `"<missing>"` = 키 없음 표지, 경로 2 null). 손으로 적을 재실행도 없다.
- 결측(`MISSING`) 0행. 감사 실행 전 수정 #2(원 행 로그 보관)는 쓸 일이 없었다.
- **K-7 `None` 경우: 없었다**(1절, 3.1절). 사용자 결정 2의 "관문 무관 경로에서 짝이 갈라짐" 기재는 해당 없음.
- **`FORCED_REVOKED_NO_REEVAL`: 없었다**(6절).
- K-8 (a)·(c) 토양 모드 전 LOC: 0건(사용자 결정 4의 stop 조건 미발생).

## 10. 실행 전 감사와 사용자 결정 반영

| 감사 항목 | 처리·결과 |
|---|---|
| [실행 전 수정] plan JSON 꼴, 한 폴더 실행 | `rem_batch_plan.json`(`rows`·`pool` 키, 10행 `pcore`). 한 번의 `s9_batch run`으로 한 폴더에 10행 |
| [실행 전 수정] 재실행 때 원 행 기록 보관 | 재실행 없음 |
| [실행 전 수정] prelaunch~postrun master 고정 | 문서·마스트 가지는 prelaunch 전에 병합(`88e2880`). 실행 중 커밋 0 |
| [확인 필요] 계획 풀 | 사용자 결정 1: P만. 10행 `pcore` |
| [확인 필요] K-7 None → 부분 통과 | 사용자 결정 2: 부분 통과 유지. 해당 경우 없음 |
| [확인 필요] `FORCED_REVOKED_NO_REEVAL`과 K-10 | 사용자 결정 3: 현행 유지, 경로 2 명세에 같은 이름·조건을 결과 전에 넣음(`recount_rem.py` 16·843행). 해당 경우 없음, F 분류 두 경로 일치 |
| [확인 필요] K-8 토양 모드 전 LOC | 사용자 결정 4: 문구대로 stop 유지. 해당 경우 없음 |
| [기록] 해석 2 K-2 범위 | 0.2.1절 기재 의무 문장 |
| [기록] 해석 7·8, gate_scan, CRLF, 이전 흔적 없음 | 변경 없음. 판정 도구는 감사 뒤 바뀌지 않았다(`49be3d10…`) |

- **저장본의 성격(공개)**: `rem_prelaunch_audit.md`(sha `0abe26cc…`, 저장 11-09 23:50:02, prelaunch 23:55:22 전)는 verif-protocol-auditor 리포트 **원문이 아니다.** 메인 세션이 원문을 요약·편집해 저장한 판이다. 파일 머리말은 "원문을 옮겨 저장"이라고 적었지만, 규칙 10절 #1의 "그대로 저장"과는 다르다. 발견 건수(차단 0 / 실행 전 수정 3 / 확인 필요 4 / 기록 8)·등급·처리는 원문과 같다(메인 세션 확인).
- 원문에 있던 비고 하나가 저장본에서 빠졌다: **"K-9는 같은 함수로 다시 유도하므로 사실상 항진이다."** 판정 도구의 K-9는 `MISSING`을 붙인 같은 함수로 다시 검사하므로 거짓이 되기 어렵다. 이번 결과에서는 결측이 0행이고, 경로 2도 rc·result.json·블록 정상 여부를 따로 세어 결측 0을 확인했다(경로 2 K-9 `scope`도 "always consistent … by construction"이라 같은 한계가 있다). 따라서 K-9 참은 결측 0의 독립 확인이 아니라 일관성 확인으로 읽는다.

## 11. 두 경로 재집계 (K-10)

### 11.1 경로

| 경로 | 방법 | 출력 | 잠정 등급 |
|---|---|---|---|
| 1 | 판정 도구 `las_k1_rem_judge.py judge`(`49be3d10…`, python-expert 구현, 메인 세션 실행) | `judge_REM.json`(`f2759451…`) | `통과` |
| 2 | control-expert 독립 재집계 `recount_rem.py`(`dfe1826f6da38f6ceef1b61bd9c40c5fa91941bc70de081254b2a89b5f309d61`). 판정 도구·프로젝트 모듈을 열지도 import하지도 않는다. result.json·batch.json·명령 npz·규칙만 읽는다. 출처를 경로 1과 다르게 둔다(LOC: `soil.t_loc_s`·decision 먼저, $t_S$: `mode_starts` → 사건, 취소: 사건 → meta) | `path2_REM.json`(`5ecde300…785f`) | `통과`, `stop_keys` 빈 목록, `ok: false` 항목 0 |

- 경로 2 출력 sha는 경로 1 실행 전에 메인 세션에 넘겨 기록됐다(8절). 그 뒤 고치지 않았다. 판정서 작성 때 다시 해시해 같음을 확인했다.

### 11.2 대조 결과 (허용 오차 없음)

- 대조 스크립트: `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\k1rem_k10\k10_compare.py` → `…\k1rem_k10\k10_result.json`. 정수·불리언·문자열은 `==`, float는 비트 동일(`==`)로 비교했다.

| 비교 대상(규칙 9.2) | 항목 수 | 일치 |
|---|---|---|
| 경로 2 출력 sha 고정, 규칙 sha | 2 | 2 |
| 두 경로가 함께 읽은 입력 파일 sha | 16 | 16 |
| 행별 상태(10행) | 10 | 10 |
| $L_1$ 튜플($n_{loc}$, $n_P$, $n_S$, dP, `t_P_s`, `t_S_s`, `post_revoke`, $n_{loc}-n_P$) | 80 | 80 |
| decision 표(건수, 행마다 `t_loc_s`·`t_P_s`·`t_S_s`·$n_{loc}$·$n_P$·$n_S$·dP·r4·`would_block`·`applied`·`post_revoke`·`last_revoke_n`·`restart_n`·**`struct_zero`**·기록 주기 일치) | 235 | 235 |
| 행 기록(취소 주기, 토양 모드 시작, LOC 주기, E3c10, 끝 기록 6종, 결측 사유, `rerun_of`) | 120 | 120 |
| 짝 결과(K-7, ③, gateon 경로, gateon R4 순서, 명령 동일 여부) | 10 | 10 |
| FLAG 건수와 내용(THIN_MARGIN, LATE_R4, SHADOW_RELOC 건수·struct_zero·항목, PAIR_DIVERGE, GATEON_PATH, OLD_CTRL_SHIFT 건수·8행 값, 하네스 대조 4행) | 20 | 20 |
| 조건 ①·③, K-0~K-9 stop 없음 | 3 | 3 |
| 등급 | 1 | 1 |
| F1·F2 경로 분류와 진단(정보용: 분류, `valid`, `FORCED_AT_L1`, `FORCED_PAIR_L1`, 취소, 재평가, 늦은 적용) | 14 | 14 |
| 예측 P-1~P-11 안/밖 | 11 | 11 |
| **합계** | **522** | **522(불일치 0)** |

- **첫 불일치: 없음.** 그래서 불일치 뒤에 맞춘 항목도 없다. 두 도구 모두 결과를 본 뒤 고치지 않았다(경로 1 sha 감사 기록과 같음, 경로 2 sha 결과 전 고정과 같음).
- **K-10: 참.**

### 11.3 공개 (대조 정의와 두 경로의 범위 차이)

- **대조 때 이름 맞춤 2건(값이 아니라 이름 표기)**: 대조 스크립트는 두 출력을 본 뒤 썼다. 맞춤은 아래 둘뿐이다.
  1. gateon 경로 이름: 경로 1 `L1_APPLIED` ≡ 경로 2 `APPLIED_AT_L1`. **스크립트 머리(18행 `GATEON_LABEL_MAP`)에 선언했다.** 규칙 6절의 `GATEON_PATH` 결과 이름은 `R4_APPLIED_LATE`/`R4_NEVER`뿐이고 "$L_1$에서 적용"의 이름은 정하지 않았다. 두 도구가 각자 이름을 붙였다. 판단 근거 필드(gateon R4 decision 순서, `applied`, `struct_zero`)는 이름 맞춤 없이 따로 대조해 같았다.
  2. `rerun_of` 키 없음: 경로 1 `"<missing>"` 표지 ≡ 경로 2 null. **이 정규화는 머리 선언이 아니라 본문 80행**(`rr1 = None if r1["rerun_of"] in (None, "<missing>") else …`)에 있고, 비교 항목 이름에 `(normalized)`를 붙였다.
- **구조 어댑터 3건(값 변환 아님, 공개)**: 두 출력의 필드 꼴이 달라 아래처럼 묶어 비교했다. 값은 바꾸지 않았다.
  1. FAULT·WARN 이름: 경로 1 `end.fault_warn_events` 한 목록 ↔ 경로 2 `faults` + `warn_names` 두 목록을 합친 것. 양쪽 모두 정렬해 비교했다(78행). 10행 모두 양쪽 빈 목록이다.
  2. 조건 ③: 경로 1 `conditions.③` 불리언 하나 ↔ 경로 2 `conditions.3_PAIR`의 짝별 `cond3`에 `all()`을 쓴 값(122행). 짝별 `cond3`는 따로 대조했다(88행, R7·R8 모두 같음).
  3. stop 여부: 경로 1 `k_checks` K-0~K-9 `ok` 모두 참 ↔ 경로 2 `stop_keys` 빈 목록(124행). 두 경로의 K-0~K-2 범위가 다르므로(아래) 이 항목은 "stop 없음"이라는 결론의 일치이고, 항목별 일치가 아니다.
- **PAIR_DIVERGE 계수 조건(앞서 짚은 차이 1)**
  - 경로 1은 짝 명령이 다르면 조건 없이 센다(`same is False`). 경로 2는 짝 gateoff가 `POS`일 때만 센다(규칙 3.4 "$L_1$ dP > 0이면 … 다르면 FLAG").
  - 명령 동일 판단의 재료도 다르다. 경로 1은 npz 안 `t_s`·`issued_u_m_s` 배열 내용 해시이고, 경로 2는 npz 파일 sha256이다.
  - 이번 결과에서는 두 짝 모두 gateoff `POS`이고 두 정의 모두 "같음"이다. 그래서 두 계수 조건이 같은 값(0)을 낸다. 차이는 결과에 닿지 않았다. **짝 gateoff가 `POS`가 아니면서 명령이 다른 경우에는 두 경로가 갈라질 수 있다.** 규칙 3.4의 문맥("$L_1$ dP > 0이면 … 다르면 FLAG")은 경로 2와 맞고, 6절 FLAG 목록("`PAIR_DIVERGE`: 짝 명령 sha가 다름", 조건 없음)은 경로 1과 맞는다. **어느 쪽이 맞는지는 미확정이며, 이번 결과에는 영향이 없다. 다음 판에서 정한다.**
- **K-0~K-2 범위(앞서 짚은 차이 2)**
  - 경로 2의 K-0·K-1·K-2는 부분 범위다. K-0은 규칙 sha(`.sha256`, 기대 상수)만, K-1은 행 HEAD 동일·dirty·batch HEAD만, K-2는 기록된 sha(`c2.py`·`zero_calibration.py`)의 batch↔result 동일과 F `module_sha256` 일관성만 본다. 경로 2는 prelaunch·postrun·도구 sha·감사 리포트 sha·blob을 읽지 않는다.
  - 그래서 **도구 sha 사슬, prelaunch·postrun HEAD, 기록 없는 7개 파일 sha, blob, 감사 리포트 sha는 두 경로로 독립 확인한 것이 아니다.** 이 부분은 경로 1(K-0~K-2)과 prelaunch·postrun 기록, 그리고 판정서 작성 시점(08:53:05, HEAD `88e2880`, `00c9770` 병합 전)에 control-expert가 직접 다시 계산한 값(`git rev-parse HEAD` = `88e2880`, `git status --porcelain --untracked-files=no` 0줄, `git diff --quiet 88e2880 HEAD -- 03_src 02_params 04_scripts` 종료 0(그 시점 HEAD = `88e2880`), 9개 파일 작업 트리·blob sha와 DLL sha, `c2.py` blob = `859deef` blob, 도구·감사 리포트·규칙 sha)으로 확인했다. 모두 같다.
  - 직접 재계산 스크립트: `…\scratchpad\k1rem_k10\blob_check.py`(작업 트리·HEAD blob 재해시, 9/9 일치, `c2_blob_eq_859deef` 참). 파일·DLL·도구 해시는 PowerShell `Get-FileHash`.
  - K-3~K-9는 경로 2도 전체 범위로 보았고(`scope` "full from records"/"full") 모두 참이다.

## 12. 결론

- **판정: `통과`.** K1 조건부 채택의 남은 근거 공백(adopt 판정 `판정 불가`의 원인, 균일 연약 지면 Chrono에서 $L_1$ dP의 부호)을 채택 대상 제어기로 직접 쟀다.
  - J2 상단·중단·하단 ×1.0, J2 상단 ×1.1(VB·V0), J1 상단 ×1.1 6행 모두 첫 R4 LOC의 dP가 **+99 ~ +206주기(9.9~20.6 s)**로 문턱(dP > 0)보다 크다. K1이 켜져도 이 행들에서 R4c30(+30 mm)이 적용된다.
  - 관문 켬 짝 2행은 실제로 $L_1$에서 적용했고, 명령이 관문 꺼짐 짝과 비트 단위로 같다. 이 조건에서 K1은 동작을 바꾸지 않는다.
  - 옛 제어기에서 18행이 셀 수 없었던 원인(취소 뒤 재LOC의 구조적 0)은 이번에도 3행에서 그림자로 나타났다(`SHADOW_RELOC` 3/3 `struct_zero`). 하지만 keep으로 첫 LOC의 +30 mm 목표가 남아 R4c30을 잃지 않았다.
- **K1 채택 조건 충족**: 규칙 4.2 `통과` = "adopt 9절 전환 절차의 승인 조건 충족". 조건 ①(MUST, `POS` 6/6, J2 ×1.1 `POS` 2/2), ②(PATCH, 기지 S-Ch 2행 dP −20, 기지 행뿐), ③(짝 2/2)이 모두 참이다. **착수(프리셋 기본 켬, 태그 `_K1` 전환)는 메인 세션이 사용자에게 알리고 승인을 받은 뒤 한다.**
- 알려진 한계(채택 뒤에도 남음): K1이 첫 R4 LOC를 막으면 R4c30이 끝까지 없다는 경로가 Chrono에서 확인됐다(F2 `FORCED_R4_NEVER`). 채택 대상 균일 연약 지면 행에서는 $L_1$ dP가 커서 이 경로가 생기지 않았다.

## 13. 다음 할 일 (메인 세션)

1. (완료) verif-protocol-auditor `[시점] 판정 후` 감사: 차단 0, 이 판에 문구 반영.
2. integrity-checker 뒤 판정서 커밋(결과 JSON은 로컬 전용). decision_log 한 줄.
3. **사용자 승인 요청**: adopt 9절 전환 절차 착수(9.1 프리셋 → 9.2 태그 `final_C4G2_LAS_K1`·`final_C4G2_P3_LAS_K1`·`ABL_LAS_K1`, 태그 소비자 조용한 실패 점검 → 9.3 전환 전 재현 러너 → 9.4 회귀 G-1~G-7 → 9.5 `[시점] 전환 후` 감사 → 9.6 문서). 구현은 python-expert(worktree), 병합·커밋은 메인 세션.
   - **전환 때 근거 인용 교체(메인 세션 결정)**: adopt 9.4 G-7의 "K1 켬 Chrono 근거는 S-Ch gateon 1행"과 9.6의 판정 근거 "`las_k1_rules_adopt.md`" 인용은 전환 때 실제 근거로 바꾼다. 실제 근거는 **adopt2 규칙(`las_k1_rules_adopt2.md`, `fb3a5696…`)과 이 판정서(R7·R8 관문 켬 짝, F2 강제 막힘 진단)**다. 메인 세션이 이렇게 정했다. adopt 판정은 `판정 불가`였으므로 adopt 규칙만으로는 전환 근거가 되지 않는다.
4. 전환 뒤(범위 밖, 사용자 결정 2026-11-09): LAS-b P5r4 + K1 재판정 규칙.
5. 기록 권고: 9.6 명세 새 절에 6절의 알려진 한계(F2)와 7.1절의 VB 이동(플랜트 설정에 따른 LOC·토양 모드 시각 차)을 넣는다.

## 14. 한계

- 판정 행에서 "막힘 → 취소 → 재평가" 경로는 관측되지 않았다($L_1$ dP > 0, 3.2절). 그 경로는 F2(정보용, 강제 막힘으로 궤적이 판정 행과 다름)와 코드 읽기로만 봤다. F1은 취소가 나지 않아 경로 ①을 보지 못했다.
- PATCH ②는 기지 행(S-Ch 2행)뿐이다. 패치 키에서 경로 ①(막힘 → 취소 → 재평가)이 나타날지는 모른다. 패치 키에서는 K1이 R4c30을 막는 것이 의도된 동작이다.
- 대상 밖: 경사, 오거 중·하단 ×1.1, J1 ×1.0 LAS-b, S1, 잡음 시드, t180, 운용 중량 +20 %. J1 ×1.0은 옛 제어기 11행 dP +49~+51로 대신한다(제어기·플랜트 차이 한계). 이번 결과로 보면 VB 플랜트는 옛 V0 행보다 LOC를 늦추고 dP를 키우는 쪽이었다(7.1절).
- ×1.0에서 VB 효과와 LAS-b 효과는 나누지 않았다(7.1절, 추정).
- 실행 중 편집 뒤 되돌림은 K-2 대조로 잡지 못한다(0.2.1절).
- 이 판정은 Chrono 1회 실행(시드 20261026, 압력 normal, IMU ideal, `--threads` 4, P코어)이다. 스레드 수·풀이 다르면 결과 비트가 달라질 수 있다(CLAUDE.md SCM 실행 규칙).
