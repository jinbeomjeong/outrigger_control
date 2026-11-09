# K1 조건부 채택 판정 기준 — 저장 Chrono SCM 결과의 그림자 dP (봉인 원판)

- 작성: control-expert, 2026-11-09
- 상태: **원판. 저장 Chrono 결과의 $t_P$·$t_S$·`decisions`·사건 값을 읽기 전에 봉인한다.** 이 판을 바꾸려면 새 판(rev1 …)을 만들고, 그 판이 판정 결과를 보기 전인지 본 뒤인지를 첫머리에 적는다.
- 파일 이름: 요청의 `las_k1_adopt_rules.md` 대신 **`las_k1_rules_adopt.md`**로 했다. `.gitattributes`의 기존 줄 `06_analysis/02_control/verif_matrix/las_k1_rules* -text`가 이 파일과 `.sha256`을 그대로 덮는다. 그래서 main checkout에 이 두 파일 밖의 변경(`.gitattributes` 수정)이 필요 없다.
- 사용자 결정(2026-11-09 21:4x, S-Ch 판정서 10.4 #3)
  1. K1(R4c30 평탄 시작 순서 관문)을 **조건부로** 채택한다.
  2. 저장된 Chrono 연약 지면 결과의 `controller_meta.soil`에서 $t_P$·$t_S$를 읽어 그림자 dP를 센다. **새 실행은 하지 않는다.**
  3. R4c30을 켜야 할 행이 모두 dP > 0이면 프리셋 기본값을 켜고, 새 태그를 붙이고, 전환 뒤 감사를 거친다(9절).
  4. 그다음 LAS-b P5r4+K1을 새 봉인 규칙과 Chrono로 다시 판정한다. **이 규칙의 범위가 아니다.**
- 이어받는 규칙: K1 원판 `las_k1_rules.md`(`2742c976…e4a0`), rev1 `las_k1_rules_rev1.md`(`eeee4ab9…b4d3`), S-Ch 계획 `las_k1_sch_plan.md`(`b0fe744f…6d9d`)·rev1(`d8f957cb…9295`). K1의 정의(원판 1.1)는 바꾸지 않는다. 이 규칙은 그 정의를 저장 결과에 그림자로 적용하는 방법과 채택 판정만 정한다.
- 규약
  - 제어: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 다리 행정 속도 명령 [m/s]).
  - 시각은 Chrono 절대 시각 [s]이다. 시각 비교는 모두 정수 주기 $n$으로 한다(4.1절). 부동소수 시각끼리 직접 비교하지 않는다.
  - 이름 구분(세 가지 "K1")
    - **이 규칙의 K1** = LAS-b K1, R4c30 순서 관문(`SlopeClearanceMarginSettings.flat_soil_margin_order_gate`, 커밋 `123e6da`).
    - 옛 touch-phase K1(2026-11-05 탈락, 코드 유지·기본 끔)과 다르다.
    - 하네스 키 토큰 `K1`(크롤러 강성 ×1)과도 다르다.

| 기호 | 정의 | 단위 |
|---|---|---|
| LOC | 크롤러 이탈 확정(`_confirm_liftoff`). 사건 `crawler_liftoff_confirmed` | — |
| R4 평가 LOC | R4c30 조건(`_is_flat_soil_margin_due`)이 참이었던 LOC(3.1절) | — |
| $t_{LOC}$, $n_{LOC}$ | 그 LOC의 시각, 그 주기 | s, 주기 |
| $t_P$, $n_P$ | 그 LOC를 확정한 S-1 평탄 창 꼬리의 첫 표본 시각(`soil.plateau_start_s`), 그 주기 | s, 주기 |
| $t_S$, $n_S$ | 그 LOC 시점의 가장 최근 토양 모드 시작 시각(`soil.soil_mode_start_s`), 그 주기 | s, 주기 |
| dP | $n_P - n_S$. K1은 dP ≤ 0이거나 $t_P$·$t_S$ 중 하나가 없으면 R4c30을 막는다 | 주기 |

## 0. 목적

- K1은 R4c30(평지 토양 틈 목표 +30 mm)을 $n_P > n_S$일 때만 켠다. 하네스(S-C 160줄, Y-0b·Y-0c 18줄)에서는 진짜 연약 지면이 dP ≥ +31, 패치가 dP ≤ −4였다.
- S-Ch(Chrono 패치 1키)에서 dP는 −20이었다. 하네스 P0(−4~−8)보다 약 12주기 음수 쪽이다.
- 같은 쪽 치우침이 진짜 연약 지면 Chrono에도 있으면, K1이 R4c30을 켜야 할 행에서 막을 수 있다. 이 규칙은 저장된 Chrono SCM 결과에서 이를 확인한다.
- 판정 대상은 "K1이 켜졌다면 각 R4 평가 LOC에서 R4c30을 막았을까"다. 행의 명령·결과가 K1에 따라 어떻게 바뀌는지는 보지 않는다(12절 한계).

## 1. 봉인 전에 본 것 (공개)

### 1.1 저장 Chrono 결과의 $t_P$·$t_S$ 값 (이미 본 것)

| 행 | 집합 | 본 값 | 본 때 |
|---|---|---|---|
| `S9/batch_V5-LAS-K1-CHRONO_20261109_193952/SCh_G1_J2FL_B_top_Fs4_VB_gateoff` | A(PATCH) | `decisions` 1건: $t_P$ 34.9 s, $t_S$ 36.9 s, dP −20, `would_block` 참, `applied` 참 | S-Ch 판정(결과 뒤) |
| `…/SCh_G1_J2FL_B_top_Fs4_VB_gateon` | A(PATCH) | 같은 LOC, 같은 값, `applied` 거짓(`_SKIPPED:order`) | S-Ch 판정(결과 뒤) |
| `S9/batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ2FL`(옛 제어기) | B(PATCH) | `controller_meta.soil.t_P_s` 33.0 s, `soil_mode_t_s` 35.0 s(→ dP −20). 이탈 33.02 s, LOC 35.4 s, phases, `p3b.checks` | S-Ch 판정서 7.5절(결과 뒤 처음 읽음) |

- 따라서 PATCH 조건(6.1 ②)의 일부(A의 S-Ch 2행)는 봉인 전에 결과를 알고 있다. 판정서에서 "봉인 전 기지 행"으로 따로 표시한다.
- 위 세 행 밖의 저장 Chrono 행에서 $t_P$·$t_S$·`decisions`·사건 시각을 이 규칙을 쓰려고 읽지 않았다.
- control-expert의 앞선 판정(FINAL-REP·RV·G6·D424 등, 명세 425~433절)이 사건 이름·LOC 시각·토양 모드 유무를 본 적이 있다. 그러나 $t_P$(`plateau_start_s`)는 그 판정 항목이 아니었다. 이 규칙을 쓰는 동안 그 문서의 해당 수치를 다시 찾아보지 않았다.

### 1.2 이 규칙을 쓰려고 이번에 본 것

- K1·S-Ch 규칙 4개, S-Ch 판정서 전문, K1 원판의 0·1·3절.
- 명세 429.9절(R4c30 채택 근거).
- 코드 `03_src/outrigger_sim/control/c2.py`
  - `_confirm_liftoff`, `_revoke_loc`, `_apply_slope_clearance_margin`, `_is_flat_soil_margin_due`, `_flat_soil_order_periods`, `_note_flat_soil_order_decision`, `_soil_meta`, `_slope_clearance_margin_meta`, 토양 모드 시작부.
  - 사건 이름 상수.
  - 필드 이름의 git 이력(`git log -S`): `"t_P_s"`·`"soil_mode_t_s"`·`soil.plateau_start_s = tail[0]` 꼴은 `db3e9b4`(10-26)부터 같다. 토양 모드 시작은 `c60a7cd`(11-09) 리팩터 전에도 같은 시각에 `soil_mode_start_s`를 쓰고 같은 사건을 냈다. `mode_starts`는 `4dd30ae`(11-09), `order_gate.decisions`는 `123e6da`(11-09)부터 있다.
- `v5_options.py`의 태그 상수, `pre_las_preset_runner.py` 머리, 프리셋 `with_10hz_d1` 서명.
- **저장 결과 300개 result.json의 메타 스캔**(2.5절 도구). 스캔이 출력한 것은 다음뿐이다.
  - 경로, 파일 sha256·크기
  - 최상위 `action`, `args`의 입력 키
  - `c2_setup`의 preset·soil_enable·k1_order_gate·expect_controller 이름/ok
  - `controller_meta`의 키 이름, `revision`·`design`·`period_s`
  - `controller_meta.soil`의 **키 이름**과 `settings.enable`
  - `controller_meta.slope_clearance_margin`의 키 이름, `settings` 값, `order_gate` 키 이름·`enabled`
  - `code_state.git_at_start.head`, `c2_soil`·`events` 유무(불리언)
  - 행 3개(FINAL-R-C4G2 1, g8c3 1, hash_check 1)의 최상위 키·`case` 이름·`floor_plane`·`c2` 키 이름(비SCM 여부 확인)
- 스캔은 파일 전체를 JSON으로 읽지만 위 목록 밖의 값은 내보내지 않았다. `t_P_s`·`soil_mode_t_s`·`t_loc_s`·`mode_starts`·`decisions`·`events`·`phases`·판정 블록 값은 보지 않았다.

## 2. 대상 집합

### 2.1 모집단 U

- `C:\workspace\outrigger_control\07_results\S9\` 와 `…\07_results\S9_merge\` 아래 모든 깊이의 파일 이름 `result.json`(대소문자 그대로). 이 봉인 시점의 목록은 **300개**다.
- 다른 폴더(worktree, `06_analysis`, `07_results/S1`~`S8`)와 다른 이름의 결과 파일(`*.jsonl`, `batch.json`)은 넣지 않는다.
  - `batch_V5-JP-V0_20261108_131212`, `batch_V5-JP-VB_20261108_115631`에는 `result.json`이 없어 U에 없다.

### 2.2 선택 규칙 (메타만, 순서대로 처음 걸린 사유로 제외)

| 단계 | 조건(거짓이면 제외) | 제외 사유 이름 |
|---|---|---|
| S0 | 파일이 JSON으로 읽힌다 | `load_error` |
| S1 | 최상위 `action == "level"`(run_S9 폐루프 레벨링) | `not_run_S9_level` |
| S2 | `args.soil` ∈ {`G1`, `J1`, `J2`, `S1`}(SCM 토양 세트) | `no_scm_soil_arg` |
| S3 | `controller_meta.soil.settings.enable is True`(토양 대응 켬) | `soil_response_off` |
| S4 | `controller_meta.soil`에 키 `t_P_s`, `soil_mode_t_s`, `t_loc_s`가 모두 있다(값은 보지 않음) | `soil_meta_fields_missing` |
| S5 | `controller_meta.slope_clearance_margin.settings.flat_soil_margin_m == 0.03`(R4c30이 있는 제어기) | 참이면 **집합 A**, 거짓이면 **집합 B** |

- S1에서 빠지는 것: `machine`·`single-pad`·`settle_ramp` 진단과 `action`이 없는 run_S8C형 결과(최상위 `floor_plane`, `args` 없음. 강체 평면 바닥 L1, FINAL-R-C4G2·g8c3·P3-10·m3·v4·soil_restore). 이들은 SCM 결과가 아니다.
- 바닥 분류(행의 `args`만 쓴다)

| 분류 | 규칙 |
|---|---|
| `PATCH` | `args.soil_patch`가 비지 않은 문자열이고, `,`로 나눈 각 항목 `<다리>:<토양>`의 토양 집합이 `{args.soil}`과 다르다 |
| `UNIFORM_SOFT` | `PATCH`가 아니고 `args.soil` ∈ {`J1`, `J2`, `S1`} |
| `UNIFORM_G1` | `PATCH`가 아니고 `args.soil == "G1"`(패치 토양이 바탕과 같은 `FL:G1`·`RR:G1` 포함) |

### 2.3 건수와 목록 sha256

| 집합 | 뜻 | 건수 | 정규 목록 sha256 |
|---|---|---|---|
| U | 모집단 | 300 | `41e01c20e45400151120e3667f3805c0fad98a279ba50fb02c054d162a1ccd79` |
| **A** | 판정 집합(R4c30 제어기) | **74** | **`2e7a1a5f70231e4662fbb985aa8e50c3983d6788bfb889800b27a086457aa9d2`** |
| B | 보조 집합(R4c30 없는 옛 제어기, 기록만) | 43 | `50622923473e9b05aec58513d7a76b739a040a5cd063c519f751bc9926b561c9` |
| E | 제외 | 183(`not_run_S9_level` 150, `soil_response_off` 33) | `ae171b438318ada7a128adc26885a869d34345080fa6a99f362467a5d73bd473` |

- A 바닥 분류: `UNIFORM_SOFT` 50(평지 32, 경사 18), `PATCH` 6(D1-CHRONO 2, FINAL4 2, S-Ch 2), `UNIFORM_G1` 18(k1soil_G1 15, JOURNAL-AUGER 3).
- A 태그(`args.expect_controller`): `final_SGS_R4` 31, `final_C4G2` 24, 없음 15(k1soil_G1), `final_C4G2_P3` 2(D1-CHRONO), `final_C4G2_P3_LAS` 2(S-Ch). **LAS-b가 켜진 행은 S-Ch 2행뿐이다**(12절 한계).
  - `batch_k1soil_G1_20261105` 15행은 옛 touch-phase K1 후보 실험(경로 `04_scripts/03_control/touch_phase/chrono_runners/k1soil_g8c/`)이다. 바닥이 `UNIFORM_G1`이라 NEUTRAL_G1 또는 NONE이 되고 등급에 들어가지 않는다.
- A 모든 행: `controller_meta.period_s` 0.1, `events` 있음, `c2_soil` 있음, `git_at_start.head` 있음. `mode_starts` 키 2행(S-Ch), `order_gate` 키 2행(S-Ch).
- B 바닥 분류: `UNIFORM_SOFT` 31, `PATCH` 10, `UNIFORM_G1` 2. 태그 없음, `git_at_start` 없음, `period_s` 0.1.
- 행 목록 전체(경로·분류·인자·파일 sha256)는 부록 A·B·C다.

### 2.4 정규형

- 정규 목록 텍스트: 집합의 각 행에 한 줄 `<07_results 기준 상대 경로, 구분자 '/'>` + TAB + `<result.json 파일 sha256(소문자 16진)>` + LF. 줄은 바이트 순서로 정렬한다. UTF-8, BOM 없음, 마지막 줄도 LF로 끝낸다.
- 목록 sha256 = 그 텍스트 바이트의 sha256.

### 2.5 목록을 만든 도구 (scratchpad, 기록)

| 파일 | sha256 |
|---|---|
| `C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\k1adopt\meta_scan.py` | `7ea661a363fdc52b8d0abedd5ba2aa9c016a5477d8956c5de3ac01d489a8eddc` |
| `…\k1adopt\build_list.py`(2.2절 규칙의 구현) | `460db43d57f55981d0e62cd5199ac5ef3bb9d7c715d7a0a0e9f90b053c6f5361` |
| `…\k1adopt\make_appendix.py` | `8cf77d834e2286115a771fa2e901b667dc8c4bde51daeb18c56f5dd14b23d0b5` |
| `…\k1adopt\meta_scan.jsonl`(스캔 출력, 300줄) | `1f42288f95793363e356c3e2d100d6c30cc6b5ee95607ca20f9658b97f3e1edc` |

- 실행: `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B <파일>`(PowerShell, 2026-11-09 21:5x).
- 판정 도구(10절)는 2.2절 규칙을 독립 구현해 같은 A·B·E 목록 sha를 다시 내야 한다(5절 K-1).

### 2.6 고정

- 판정은 **부록 A의 74행 그대로**를 대상으로 한다. 봉인 뒤 U에 새 result.json이 생겨도 A에 넣지 않는다. 판정서에 U 재계산 건수·sha만 기록한다.
- A의 어느 행이라도 파일 sha256이 부록과 다르거나 파일이 없으면 **stop**(5절 K-2)이다.

## 3. 분류

### 3.1 R4 평가 LOC

- 한 행의 R4 평가 LOC는 `events`(최상위 `events` 목록, 항목 `{t_s, name}`) 가운데 다음 사건이 난 LOC다.
  - **적용**: `name.split(":", 1)[0] == "INFO_LOC_FLAT_SOIL_MARGIN"` — **정확 일치**. `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED…`는 접두어가 같지만 적용이 아니다.
  - **관문 막음**(관문 켬 행만, A에서는 S-Ch gateon 1행): `name == "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"`.
- 사건 시각 $t_R$의 주기 $n_R$ = round($t_R$/0.1)이 그 LOC의 $n_{LOC}$다.
- 근거: `_confirm_liftoff`가 같은 `t_s`로 LOC 사건과 R4 결정을 낸다. 관문 꺼짐에서는 R4 조건 참 ⇔ 적용이다(`is_applied = is_r4_due and not (is_gate_on and would_block)`).
- 경사 여유 E3c10(`INFO_LOC_CLEARANCE_MARGIN`)이 선 LOC는 R4를 평가하지 않는다(`elif`). K1과 무관하므로 R4 평가 LOC가 아니다. 그 건수는 기록한다.

### 3.2 행 분류 (A)

| 행 분류 | 조건 | 역할 |
|---|---|---|
| **MUST**(R4c30을 켜야 할 행) | 바닥 `UNIFORM_SOFT` + R4 평가 LOC ≥ 1 | 그 행의 **모든** R4 평가 LOC에서 dP > 0이어야 한다 |
| **PATCH**(K1이 막아야 할 행) | 바닥 `PATCH` + R4 평가 LOC ≥ 1 | 모든 R4 평가 LOC에서 dP ≤ 0(또는 $t_P$·$t_S$ 없음 = 막음)이어야 한다 |
| **NEUTRAL_G1** | 바닥 `UNIFORM_G1` + R4 평가 LOC ≥ 1 | 기록만. K1이 막으면 R4c30 이전 동작(10-30 전 G1 결과)으로 돌아간다 |
| **NONE** | R4 평가 LOC 0 | 기록만(토양 모드 사용 수, E3c10 LOC 수, 이유별 건수) |

- MUST의 근거: R4c30 채택 근거(명세 429.9)인 E-6 6/6 회복이 J2 균일 연약 지면이었다. 하네스 "진짜 연약 지면"도 J1·J2·S1 균일(H-S-0, H-S-1, H-S-C, H-R-A-S1)이었다.
- G1 균일은 하네스 토양 모드 0/72(LAS T-3a)였다. R4c30이 필요하다는 근거가 없어 판정에서 뺀다.
- 경사 행은 바닥 분류가 `UNIFORM_SOFT`이면 MUST 후보다. R4 평가 LOC가 없으면 NONE이다(정착 기울기 > 1°이면 R4가 서지 않는다).
- 같은 `case` 이름이 여러 배치에 있으면(예: `S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` 10행) **행마다 따로** 센다. (case, 태그)별 최소도 기록한다.

## 4. 그림자 dP 계산

### 4.1 정수 주기

- $n$ = `round(t / 0.1)`. Python 내장 `round`(float64, 짝수 반올림)를 쓴다. `c2.py` `_flat_soil_order_periods`의 `round(soil.plateau_start_s / period_s)`와 같은 식이다.
- 그 행의 `controller_meta.period_s`는 0.1이어야 한다(아니면 5절 K-4 stop).
- dP = $n_P - n_S$(정수).

### 4.2 LOC 식별 (필드 대응)

- LOC 목록: 사건 `name == "crawler_liftoff_confirmed"`의 시각 → 주기.
- 모든 R4 평가 LOC의 $n_R$는 LOC 목록에 있어야 한다(K-5).
- 최종 LOC: `controller_meta.soil.t_loc_s`(None이면 최종 LOC 없음 = 마지막 LOC가 취소됨). 주기 $n_{fin}$.
- LOC 취소 수: 사건 `name.split(":",1)[0] == "INFO_LOC_REVOKED"`의 건수(기록).

### 4.3 $t_P$의 출처 (R4 평가 LOC마다)

| 경우 | $t_P$ | 상태 |
|---|---|---|
| (a) 행에 `controller_meta.slope_clearance_margin.order_gate.decisions`가 있다(S-Ch 2행) | $n_{loc}$ = round(`t_loc_s`/0.1) = $n_R$이고 `r4_due_without_gate` 참인 decision의 `t_P_s` | 아래 4.5 |
| (b) decisions가 없다(옛 제어기 72행): $n_R = n_{fin}$ | `controller_meta.soil.t_P_s` | 아래 4.5 |
| (c) decisions가 없고 $n_R \ne n_{fin}$(그 LOC가 뒤에 취소되고 새 LOC가 왔거나, 마지막 LOC가 취소됨) | 저장되지 않음 | **`UNRECOVERABLE`** |

- (c)의 근거: `_revoke_loc`이 `soil.plateau_start_s = None`으로 지우고, 다음 LOC가 덮어쓴다. 다른 기록(사건, `INFO_CLEARANCE_BIAS`, step_series)은 $t_P$를 담지 않는다. 재구성(S-1 창 재생)은 이 규칙에서 하지 않는다.
- (a)에서 같은 $n_R$의 decision이 0건이거나 2건 이상이면 K-6 stop.
- (a) 행의 최종 LOC decision `t_P_s`는 `controller_meta.soil.t_P_s`와 같아야 한다(값 동일, K-7).

### 4.4 $t_S$의 출처

- $t_S$ = 그 LOC 시점의 가장 최근 토양 모드 시작 = 토양 모드 시작 시각 가운데 주기 ≤ $n_R$인 것의 최대.
  - 같은 주기 안에서는 LOC가 토양 모드 시작보다 먼저 처리된다(K1 원판 0.1). 그래서 $n_S = n_R$인 시작은 그 LOC 뒤의 것이다. **$n_S < n_R$인 것만** 넣는다. (a) 행은 decision의 `t_S_s`와 대조한다.
- 경로 1(판정 도구): 사건 `name == "soil_mode_start"`의 시각.
- 경로 2(독립 재집계): `controller_meta.soil.mode_starts[*].t_s`(있으면, S-Ch 2행). 없으면 `controller_meta.soil.soil_mode_t_s`(그 행의 마지막 토양 모드 시작)이다. 그 주기가 $n_R$보다 작으면 그것을 쓴다. 크거나 같으면 경로 2는 사건 목록 가운데 주기 < $n_R$인 마지막 `soil_mode_start`를 쓰고, `soil_mode_t_s`의 주기가 그 값보다 커야 한다(일관성 확인).
- 근거: 토양 모드 시작부는 같은 `t_s`로 `soil_mode_start_s`를 쓰고 사건 `soil_mode_start`를 낸다(`db3e9b4`부터. `c60a7cd` 전후 동일). `soil_mode_start_s`는 LOC 취소·TOUCH 재진입에서 지워지지 않는다.
- 주기 < $n_R$인 토양 모드 시작이 없는데 R4 평가 LOC가 있으면 모순이다(R4 조건은 `soil_mode_start_s is not None`). K-8 stop.

### 4.5 LOC별 상태

| 상태 | 조건 | K1이 켜졌다면 |
|---|---|---|
| `OK` | $t_P$·$t_S$ 모두 수(유한 float), dP 계산 | dP > 0이면 적용, dP ≤ 0이면 막음 |
| `BLOCKED_MISSING` | 출처 (a)·(b)에서 $t_P$ 값이 None(키는 있음) | 막음(`_is_flat_soil_order_blocked`: None → 막음) |
| `UNRECOVERABLE` | 출처 (c) | 알 수 없음 |

- 키 자체가 없으면 S4에서 이미 빠진다. A에는 없다. 판정 때 키가 없으면 K-2(sha 불일치)가 먼저 걸린다.

### 4.6 옛 제어기의 필드 이름 대응 (필드 이름만으로 정함)

| K1 정의(원판 1.1·1.2) | decisions 있는 행(S-Ch) | decisions 없는 행(옛 제어기) |
|---|---|---|
| $t_P$ | `decision.t_P_s` | `controller_meta.soil.t_P_s`(최종 LOC만) |
| $t_S$ | `decision.t_S_s` | 사건 `soil_mode_start` / `controller_meta.soil.soil_mode_t_s` / `mode_starts`(4.4) |
| $t_{LOC}$ | `decision.t_loc_s` | R4 사건 시각, `controller_meta.soil.t_loc_s`(최종 LOC) |
| R4 조건 | `decision.r4_due_without_gate` | 사건 `INFO_LOC_FLAT_SOIL_MARGIN`(관문 꺼짐) |

- A·B 117행 모두 `controller_meta.soil`에 같은 이름 `t_P_s`·`soil_mode_t_s`·`t_loc_s`가 있다(2.3절 스캔). 이름이 다른 행은 없다. 이름이 다르면 대응시키지 않고 판정 불가로 한다(새 판 필요).
- 최상위 `c2_soil`은 `controller_meta.soil`의 복사본이다(run_S9 `"c2_soil": ctl_meta.get("soil")`). 세 키 값이 서로 같아야 한다(K-7).

## 5. 정체성·일관성 (하나라도 거짓이면 stop)

| # | 검사 |
|---|---|
| K-0 | 이 규칙 파일 sha256 = `.sha256` 기록. 판정 도구 sha256이 실행 전 감사 기록·판정 JSON·판정 때 파일에서 같다 |
| K-1 | 도구가 2.2절 규칙으로 다시 만든 A·B·E 목록 sha256이 2.3절과 같다(U는 기록만. 봉인 뒤 새 파일은 2.6절) |
| K-2 | A 74행 각 파일이 있고 sha256이 부록 A와 같다 |
| K-3 | A 각 행: `controller_meta`·`controller_meta.soil`·`events`가 dict/list다(`{"error": …}` 부분 기록 아님). `controller_meta.soil.restored_from is None` |
| K-4 | A 각 행 `controller_meta.period_s == 0.1` |
| K-5 | 각 R4 평가 LOC의 $n_R$가 `crawler_liftoff_confirmed` 주기 목록에 있다. 한 $n_R$에 R4 사건이 둘 이상이면 거짓 |
| K-6 | decisions 행: 각 R4 평가 LOC에 대응 decision이 정확히 1건(4.3 (a)). 그리고 `r4_due_without_gate` 참인 decision 주기 집합 = R4 평가 LOC 주기 집합. 관문 꺼짐 행(`order_gate` 없음 또는 `enabled` 거짓)에 `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order` 사건이 있으면 거짓. 관문 켬 행에 `INFO_LOC_FLAT_SOIL_MARGIN` 적용 사건이 있으면, 그 LOC의 decision `would_block`이 거짓이어야 한다 |
| K-7 | `controller_meta.soil`과 `c2_soil`의 `t_P_s`·`soil_mode_t_s`·`t_loc_s`가 같은 값이다. decisions 행의 최종 LOC decision `t_P_s` = `controller_meta.soil.t_P_s` |
| K-8 | 모든 R4 평가 LOC에 주기 < $n_R$인 토양 모드 시작이 있다. 경로 1·경로 2의 $n_S$가 같다. decisions 행에서는 decision `t_S_s`의 주기와도 같다 |
| K-9 | 두 경로 재집계(10절)가 LOC별 (행, $n_R$, 출처, 상태, $n_P$, $n_S$, dP)와 행 분류·등급에서 완전히 같다 |

- stop이면 판정하지 않는다. 원인을 판정서에 적고 사용자에게 묻는다. 규칙을 고칠 일이면 rev1을 만든다.

## 6. 판정

### 6.1 조건

- ① **MUST**: MUST LOC 가운데 `OK` 건수가 ≥ 1이다. 그리고 MUST의 모든 LOC가 `OK`이며 dP > 0이다.
- ② **PATCH**: PATCH LOC 가운데 `OK` 또는 `BLOCKED_MISSING` 건수가 ≥ 1이다. 그리고 PATCH의 모든 LOC가 `OK`이며 dP ≤ 0이거나 `BLOCKED_MISSING`이다.
  - S-Ch 2행은 봉인 전 기지 행이다(1.1절). 그래서 ②는 그 밖의 PATCH LOC(D1-CHRONO·FINAL4)도 따로 센다. 기지 행을 뺀 PATCH LOC가 0건이면 ②는 참이지만 "기지 행뿐"으로 판정서에 공개한다.

### 6.2 등급 (위에서부터 처음 해당하는 것)

| 등급 | 조건 | 행동 |
|---|---|---|
| `stop` | 5절 K-0~K-9 중 하나라도 거짓 | 판정 없음. 원인 공개, 사용자에게 묻는다 |
| `미달` | MUST에 `OK`이고 dP ≤ 0인 LOC 또는 `BLOCKED_MISSING` LOC가 1건 이상 | **전환하지 않는다.** K1은 지금 정의로는 채택하지 않는다. 해당 LOC 표(행, $t_P$, $t_S$, dP, 바닥·오거·질량)와 함께 사용자에게 다음 결정을 묻는다 |
| `판정 불가` | MUST LOC 0건(`OK` 0), 또는 MUST에 `UNRECOVERABLE` LOC가 1건 이상 | **전환하지 않는다.** 건수·행을 공개한다. 선택지(예: 관문 꺼짐 + decisions 기록 재실행)는 사용자에게 묻는다. 새 실행은 사용자 승인 뒤에만 한다 |
| `부분 통과` | ①은 참, ②가 거짓(PATCH에 dP > 0 또는 `UNRECOVERABLE`) | **자동 전환하지 않는다.** K1은 MUST에서 R4c30을 없애지 않지만, 해당 패치 행에서 기대 효과(+30 mm 행정 제거)가 없다. 사용자에게 채택 여부를 묻는다 |
| `통과` | ①·② 모두 참 | 사용자 결정 3에 따라 **9절 전환 절차를 시작한다**(이 판정이 전환 승인 조건이다) |

- `미달`이 `판정 불가`보다 먼저다. 셀 수 있는 MUST LOC 하나가 dP ≤ 0이면, 다른 LOC가 복원 불가여도 `미달`이다.
- NEUTRAL_G1·NONE·집합 B는 등급에 들어가지 않는다(7절 기록).
- 판정 뒤 문턱(dP > 0)을 바꾸지 않는다. dP 여유가 작다는 이유로 등급을 바꾸지 않는다(7절 FLAG로만 남긴다).

## 7. 기록 (등급에 영향 없음)

- 분포: 분류별 LOC 수, dP 최소·중앙·최대, 히스토그램(5주기 폭). MUST는 행별·(case, 태그)별 최소를 적는다.
- 각 LOC: 행 경로, 바닥, 오거, 경사, 질량, $F_s$, 태그, $n_R$, $n_P$, $n_S$, dP, 출처(a/b), 상태, LOC 취소 수, $n_R - n_S$.
- FLAG
  - `THIN_MARGIN`: MUST LOC의 dP ≤ 12. 12는 S-Ch에서 본 하네스 대비 치우침(−12주기)이다. 같은 크기의 치우침이 더 생기면 막힐 수 있는 위치라는 뜻이다.
  - `NEUTRAL_G1_BLOCK`: NEUTRAL_G1 LOC 가운데 K1이 막을 것(dP ≤ 0 또는 `BLOCKED_MISSING`)의 수.
  - `MULTI_LOC`: R4 평가 LOC가 2개 이상인 행.
  - `REVOKED_AFTER_R4`: R4 평가 LOC 뒤 LOC 취소가 있는 행(4.3 (c)의 원인 확인용).
  - `B_SOFT_NONPOS`: 집합 B의 `UNIFORM_SOFT` 행 가운데 최종 LOC 그림자 dP ≤ 0인 것(아래).
- 집합 B(옛 제어기, R4c30 없음): R4 평가 LOC가 정의되지 않는다. 기록용으로 **최종 LOC**에서 $t_P$ = `controller_meta.soil.t_P_s`, $t_S$ = 4.4절(주기 < $n_{fin}$)로 dP를 센다. 둘 중 하나라도 없으면 "토양 모드 없음/LOC 없음"으로 적는다. `B_SOFT_NONPOS`가 1건 이상이면 판정서와 사용자 보고에 반드시 적는다. 등급은 바꾸지 않는다(그 행들은 R4c30 조건(정착 기울기 등)을 판정할 수 없고 제어기가 다르다).
- E3c10 적용 LOC 수(`INFO_LOC_CLEARANCE_MARGIN`), 토양 모드를 쓴 행 수, A의 NONE 이유(토양 모드 없음 / E3c10 / 그 밖)를 센다.

## 8. 사전 예측 (판정 기준 아님)

- 근거
  - 하네스: 진짜 연약 지면 R4 행 dP ≥ +31(S-C 160줄), H-S-0 ≥ +36, Y-0b·Y-0c 18줄 +31~+96. 패치 ≤ −4(S-C 5줄), H-S-A-J2 −4~−8.
  - Chrono: 패치 1키 −20(S-Ch, LAS-b 켬)과 같은 키 옛 제어기 −20(10-28). 하네스 대비 약 −12주기. 원인은 SCM 크롤러 제하·침하 경로 차이로 추정한다(S-Ch 판정서 4.2).
  - 기구: 균일 연약 지면에서는 래치 해제(토양 모드 시작)가 크롤러가 아직 하중을 받는 동안 오고, 밀어 올림 뒤에 평탄 창이 시작된다. 그래서 $t_S$가 $t_P$보다 크게 앞선다. 패치에서는 평탄 창이 먼저 서고 래치 해제가 늦다. Chrono의 치우침은 "느린 들어 올림 중 해제 조건이 차는 데 걸리는 시간"이 길어진 것이다. 이 효과가 균일 연약 지면에도 같은 크기로 작용한다고 가정한다(보수 쪽).

| # | 항목 | 예측 |
|---|---|---|
| P-1 | MUST 행 수 | A `UNIFORM_SOFT` 평지 32행 중 26~32행. 경사 18행은 0행(정착 기울기 > 1°라 E3c10 또는 미평가) |
| P-2 | MUST LOC dP | 모두 > 0. 최소 [+15, +60], 중앙 [+30, +90]. 점 예측: 최소 ≈ +19(하네스 최소 +31 − 12) |
| P-3 | `THIN_MARGIN` | 0건 |
| P-4 | PATCH 행 수(S-Ch 2행 제외) | 0~4행. LOC가 있으면 모두 dP ∈ [−30, −1] |
| P-5 | NEUTRAL_G1 | R4 평가 LOC 0~3건(하네스 G1 토양 모드 0/72). 있으면 dP의 부호는 예측하지 않는다 |
| P-6 | `UNRECOVERABLE` | MUST·PATCH 합 0~2건. LOC 취소(L1gs)는 ×1.1 J1 상단 등 일부 행에서만 날 것으로 본다 |
| P-7 | `BLOCKED_MISSING` | 0건 |
| P-8 | K-0~K-9 | 모두 참 |
| P-9 | 집합 B | `UNIFORM_SOFT` 31행 중 최종 LOC 토양 모드가 있는 행은 대부분 dP > 0. `B_SOFT_NONPOS` 0~2건. B PATCH의 10-28 spJ2FL은 −20(기지) |
| P-10 | 등급 | `통과`(확률 판단: 높음). 다음으로 가능한 것은 P-6 때문의 `판정 불가` |

## 9. 채택 뒤 전환 절차 (`통과`일 때만)

- 순서: 판정서 → verif-protocol-auditor `[시점] 판정 후` 감사(차단 0) → 판정서 커밋(메인 세션, integrity-checker 먼저) → 아래 9.1~9.6 → `[시점] 전환 후` 감사 → 문서 갱신 → (범위 밖) LAS-b P5r4+K1 재판정 규칙.
- 구현은 python-expert가 worktree 브랜치에서 한다. 병합·커밋은 메인 세션이 한다.

### 9.1 프리셋

- `C2Config.with_10hz_d1(…, flat_soil_margin_order_gate: bool = True)` 키워드를 더한다. `SlopeClearanceMarginSettings(…, flat_soil_margin_order_gate=flat_soil_margin_order_gate)`로 넘긴다.
- 클래스 기본값 `SlopeClearanceMarginSettings.flat_soil_margin_order_gate = False`는 그대로 둔다(클래스 기본 = 옛 동작, 기존 관례).
- `run_S9 --k1-order-gate`의 기본값을 `preset`(덮어쓰지 않음)으로 둔다. 지금 기본값 `off`를 그대로 두면 전환 뒤에도 run_S9 실행이 조용히 K1 꺼짐으로 돈다. `off`·`on`은 명시할 때만 덮는다. `c2_setup.k1_order_gate`에 `preset`/`off`/`on`과 실제 값(`effective`)을 함께 기록한다(래퍼와 프리셋이 겹쳐 두 번 적용되는지 감사가 볼 수 있게).
- 하네스 드라이버(K1 토큰 `K1`을 쓰는 `04_scripts/04_hydraulic/coupled/k1_targeted.py` 등)도 같다. 토큰이 없으면 전환 뒤 프리셋 값(켬)이 된다. 저장 K1off 줄을 재현하려면 명시적 꺼짐 토큰이나 `pre_k1_preset_runner.py`가 필요하다. 토큰 `K1`과 프리셋이 겹칠 때의 동작(멱등인지)을 시험으로 고정한다.

### 9.2 태그

| 설정 | 전환 전(지금) | 전환 뒤 |
|---|---|---|
| V0 / 그 밖(③ 없음) | `final_C4G2_LAS` | **`final_C4G2_LAS_K1`** |
| VB / LS(③ 켬) | `final_C4G2_P3_LAS` | **`final_C4G2_P3_LAS_K1`** |
| ABL | `ABL_LAS` | **`ABL_LAS_K1`** |

- 규칙: LAS-b 접미사 `_LAS` 다음에 순서 관문 접미사 `_K1`을 붙인다. `v5_options`에 `ORDER_GATE_TAG_SUFFIX = "_K1"`, `controller_tag(options, config)`가 `config.slope_clearance_margin.flat_soil_margin_order_gate`가 참이면 붙인다.
- `EXTEND_START_TAGS`에 `final_C4G2_P3_LAS_K1`을 더한다(③ 켬 태그 집합).
- **조용한 실패 점검(필수)**
  - `is_liftoff_slow_tag`는 지금 `tag.endswith("_LAS")`다. `_LAS_K1`에 대해 거짓을 돌려준다. 접미사 토큰을 나눠 판단하도록 고친다.
  - `with_liftoff_slow_tag`도 `_K1` 붙은 태그에 `_LAS`를 한 번 더 붙이지 않게 한다.
  - 태그 소비자 전부를 `git grep`으로 나열한다(`== "final_C4G2…"`, `in (…)`, `endswith`, `startswith`, 딕셔너리 키). 그리고 큰 실패(즉시 오류)와 조용한 실패(선택 집합이 빔)로 나눈다. 알려진 곳:
    - `run_S9.FINAL_LAS_CONTROLLER`·`FINAL_P3_LAS_CONTROLLER`·`CONTROLLER_EXPECTATIONS`
    - `s9_batch.V5_P3_LAS_CONTROLLER`·`V5_LAS_CONTROLLER`
    - `las_chrono_rows`·`las_k1_chrono_rows`·`d1_chrono_rows`
    - `fb_judge.EXPECTED_CONTROLLER_TAGS`, `las_rev_judge.CONTROLLER_TAGS`·`CONTROLLER_TAG_BY_SETTING`, `las_rev_targeted`
    - `j_p3_inputs.P3_CONTROLLER_TAGS`, `v5_rerun`, `u3_judge`, `b5_baseline_compare`, `stage3` 비교 도구
    - 관련 시험
  - 봉인된 판정 도구의 태그 상수(예: `las_k1_sch_judge.CONTROLLER_TAG`)는 고치지 않는다. 그 판정은 옛 태그 결과에 대한 것이다.
- `run_S9.CONTROLLER_EXPECTATIONS`에 새 두 태그를 넣는다. 기존 점검에 `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate == True`를 더한다. 옛 `_LAS` 두 태그는 `== False`를 점검한다. 그래서 전환 뒤 옛 태그로 돌리면 크게 실패한다(전환 전 재현 러너로만 돌린다).

### 9.3 전환 전 재현 러너

- `05_tests/unit/pre_k1_preset_runner.py`: `pre_las_preset_runner.py`와 같은 꼴이다. `with_10hz_d1`의 `flat_soil_margin_order_gate` 기본값만 False로 되돌리고 스크립트 `main()`을 부른다. 스레드 env 선설정과 import 때 패치(풀 워커 상속)도 같다.
- **기존 세 러너도 고친다**: `pre_las_preset_runner.py`, `pre_c4g2_preset_runner.py`, `pre_switch_preset_runner.py`는 각자 키워드 하나(또는 몇 개)만 되돌린다. K1 전환 뒤에는 이 러너로 돌린 옛 결과가 K1 켬으로 재현된다. 세 러너 모두 `flat_soil_margin_order_gate=False`도 함께 되돌리게 한다. 각 러너 docstring의 "어느 결과를 재현하는가"를 고친다.
- 한계(공개): 키워드 되돌리기 러너는 뒤 커밋의 다른 변경을 그대로 둔다. 저장 결과를 비트 단위로 재현하려면 그 결과의 `git_at_start` 커밋을 고정해 내보내 써야 한다(에이전트 메모리 규칙).

### 9.4 회귀 시험

| # | 시험 | 합격 |
|---|---|---|
| G-1 | `pytest 05_tests/unit` 전체 | 실패 0. 프리셋·태그를 단정하는 시험은 새 값으로 고친다. 고친 시험 목록을 보고한다 |
| G-2 | 클래스 기본(`C2Config()`, 관문 꺼짐) | 기존 단위 시험의 명령·메타 해시가 같다 |
| G-3 | 하네스 K1 켬 저장 줄 재현: K1 토큰 없이 새 프리셋으로 K1 원판 Y-Pa 165 + Y-Pb 40 + Y-Sa 30 + Y-Sb 30 + Y-T 192(Y-Sb·Y-T는 `P5r4` 후보 토큰은 그대로 둔다) | `commands_sha256`가 저장 K1on 줄과 모두 같다(래퍼 토큰 `K1` = 프리셋 구현) |
| G-4 | 전환 전 재현: `pre_k1_preset_runner.py`로 Y-0c 30 + Y-0d 40 | 저장 K1off 줄 해시와 같다 |
| G-5 | 옛 러너 재현: 고친 `pre_las_preset_runner.py`로 LAS 판정의 저장 줄 표본(예: `revA_RP0.jsonl` R4 적용 줄 전부 + 비R4 20줄) | 해시가 같다 |
| G-6 | 영향 목록(실행 없음): 저장 결과 집합 가운데 R4 평가 LOC가 있고 그림자 dP ≤ 0인 행 = 전환 뒤 해시가 바뀔 행 | 집합별 표(그림자 근거가 있는지, 바뀔 행 수)를 판정서에 붙인다. 근거 없는 집합은 "재실행 필요 시 새 태그로"라고 적는다 |
| G-7 | Chrono | 새 실행 없음. K1 켬 Chrono 근거는 S-Ch gateon 1행(`final_C4G2_P3_LAS` + `--k1-order-gate on`, 태그는 옛 이름)이다 |

### 9.5 감사

- verif-protocol-auditor `[시점] 전환 후`: 9.2 태그 소비자 표(큰/조용한 실패), `EXTEND_START_TAGS`·`_LAS`/`_K1` 접미사 판단, 래퍼(`--k1-order-gate on`, 하네스 토큰 `K1`)와 프리셋의 이중 적용, 전환 전 재현 러너 4개, `.gitattributes -text` 보호(`las_k1_rules*`, 새 도구), G-1~G-6 기록.
- 감사 차단 0일 때만 다음 단계(LAS-b P5r4+K1 재판정 규칙)로 간다.

### 9.6 문서 (메인 세션)

- `00_docs/decision_log.md`: 한 줄(조건부 채택 판정 등급, 규칙 sha, 판정서 커밋, 전환 커밋).
- 명세 `s6_control_spec.md`: 새 절(K1 R4c30 순서 관문, 근거 = K1 원판·S-Ch·이 규칙 판정서, 기본값 전환).
- CLAUDE.md "현재 기준값" 표 **제어기** 행에 넣을 문구(제안)

> 2026-11-xx부터 + **LAS-b K1 R4c30 순서 관문**(`flat_soil_margin_order_gate`, R4c30은 평탄 창 시작 주기 > 토양 모드 시작 주기일 때만; 판정 `las_k1_rules_adopt.md`) 프리셋 기본 켬 → 태그 V0 `final_C4G2_LAS_K1`, VB `final_C4G2_P3_LAS_K1`, ABL `ABL_LAS_K1`. `_LAS` 태그는 K1 전환 전 결과이고, 재현은 `05_tests/unit/pre_k1_preset_runner.py`다. **이 K1은 2026-11-05에 탈락한 touch-phase K1(코드 유지, 기본 끔)과 다르고, 하네스 키 토큰 `K1`(크롤러 강성 ×1)과도 다르다.**

- 같은 행의 기존 문구 "K1은 탈락(코드 유지, 기본 끔)"은 "touch-phase K1은 탈락(…)"으로 고친다.

## 10. 집계 도구 명세

### 10.1 경로 1 — 판정 도구 (python-expert 구현)

- 파일: `06_analysis/02_control/verif_matrix/scripts/las_k1_adopt_judge.py`(`.gitattributes` `verif_matrix/scripts/* -text`에 들어간다).
- 환경: dynamics-dev(`conda run -n dynamics-dev python -I -B`). 표준 라이브러리(json, hashlib, pathlib, statistics, argparse)만 쓴다. **프로젝트 모듈(`outrigger_sim`, run_S9, s9_batch)과 다른 판정 도구를 import하지 않는다.**
- 읽기 전용: `07_results`의 파일을 읽기만 한다. 쓰는 것은 `--out` 하나다. git은 `git rev-parse HEAD`·`git status --porcelain` 조회만 한다(`--no-git`이면 건너뜀).
- 하위 명령
  - `list --results-root <07_results> --out <json>`: 2.1~2.4절을 독립 구현한다. U·A·B·E 건수·목록 sha와 행별 분류를 낸다. 2.3절 값과 다르면 종료 2.
  - `judge --results-root <07_results> --rules <las_k1_rules_adopt.md> --out <json>`: K-0~K-8, 3~7절. 부록 A의 경로·sha 표를 규칙 파일에서 읽는다.
    - 파싱 규칙: 부록 A 표의 `경로(배치/행)` 열은 `07_results/S9/` 기준 `<배치 폴더>/<행 폴더>`다. 파일은 `07_results/S9/<배치 폴더>/<행 폴더>/result.json`이다. A에는 `S9_merge` 행도, 더 깊은 행도 없다.
    - `result.json sha256` 열은 64자 소문자 16진이다.
    - 파싱한 74행으로 2.4절 정규 목록을 다시 만든 sha가 2.3절 A 값과 같아야 한다(K-1의 일부).
- 출력 JSON(마지막 줄에도 요약 JSON 한 줄)
  - `rules_sha256`, `tool_sha256`, `git_head`, `taken_utc`
  - `files_read_sha256`(행별)
  - `k_checks`(K-0~K-8 참/거짓과 실패 행)
  - `locs`(LOC별: 행, 바닥, 분류, $t_R$, $n_R$, 출처, 상태, `t_P_s`, `t_S_s`, $n_P$, $n_S$, dP, LOC 취소 수, 기지 행 여부)
  - `rows`(행별: 분류, R4 평가 LOC 수, E3c10 LOC 수, 토양 모드 시작 수, LOC 수)
  - `summary`(분류별 건수·dP 최소/중앙/최대·히스토그램, (case, 태그)별 최소), `flags`, `set_B`(7절)
  - `grade`(`stop`/`미달`/`판정 불가`/`부분 통과`/`통과`), `grade_reasons`, `predictions`(8절 P-1~P-10 안/밖)
- 종료 코드: 0 `통과`, 1 `미달`·`판정 불가`·`부분 통과`, 2 `stop`, 3 도구 오류.
- 단위 시험(합성 result.json, `05_tests/unit/test_las_k1_adopt_judge.py`)
  1. 옛 행, LOC 1개: (b) 출처 dP 정확.
  2. R4 LOC 뒤 취소 + 새 LOC: `UNRECOVERABLE`.
  3. 마지막 LOC 취소(`t_loc_s` None): `UNRECOVERABLE`.
  4. decisions 행: (a) 출처, K-6.
  5. `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order`가 적용으로 세지지 않음(관문 꺼짐 행에서는 이 사건이 있으면 K-6/모순으로 걸림), `INFO_LOC_FLAT_SOIL_MARGIN:80`은 적용.
  6. 같은 주기 토양 모드 시작($n_S = n_R$)은 $t_S$에 넣지 않음.
  7. `controller_meta.soil` 대 `c2_soil` 값 다름: K-7 stop.
  8. MUST 0건: `판정 불가`. MUST 1건 dP 0: `미달`. `t_P_s` None: `BLOCKED_MISSING` → MUST면 `미달`.
  9. 반올림: float 그대로 `round(t / 0.1)`을 쓴다(문자열·Decimal 반올림 금지). 34.95/0.1 = 349.5 → 350, 34.85/0.1 = 348.5 → 348(짝수 반올림, dynamics-dev Python 3.12에서 확인. c2.py와 같은 식).
  10. 부록 A 파싱: 74행, sha 형식 64자.

### 10.2 경로 2 — 독립 재집계 (control-expert)

- control-expert scratchpad의 `recount_adopt.py`. 판정 도구·프로젝트 모듈을 import하지 않는다. 같은 result.json과 규칙 파일만 읽는다.
- 출처 우선순위를 경로 1과 다르게 둔다
  - $t_S$: `mode_starts`, 그다음 `soil_mode_t_s`, 마지막으로 사건(4.4절).
  - LOC 식별: `controller_meta.soil.t_loc_s`와 decisions 먼저, 사건은 대조용.
- 비교: LOC별 튜플 (행, $n_R$, 출처, 상태, $n_P$, $n_S$, dP)과 행 분류·FLAG·등급이 **완전히 같아야** 한다(K-9). 수치 비교에 허용 오차를 두지 않는다(모두 정수 또는 저장 float 그대로).
- 첫 불일치를 본 뒤 한쪽을 다른 쪽에 맞췄다면, 그 항목은 독립이 아니라고 판정서에 공개한다(S-Ch E-6a 교훈).

### 10.3 실행 순서

1. 이 규칙 봉인(지금) → 메인 세션 커밋(integrity-checker 먼저).
2. python-expert가 도구·단위 시험 구현(worktree) → 병합.
3. verif-protocol-auditor `[시점] 실행 전` 감사(규칙 ↔ 도구, 부록 A 파싱, K-검사, 종료 코드). 차단 0.
4. 메인 세션: `list` → `judge` 실행(dynamics-dev, PowerShell). control-expert: 경로 2.
5. control-expert 판정서 `las_k1_adopt_judgement.md` → `[시점] 판정 후` 감사 → 커밋.
6. `통과`면 9절. 그 밖이면 6.2절 행동.

- 이 묶음은 저장 파일 읽기뿐이다. 수 분 안에 끝난다(추정: 74행 × 수 MB). Chrono·하네스 실행은 없다.

## 11. S2D·K1 교훈 체크리스트

| # | 항목 | 이 규칙의 처리 |
|---|---|---|
| 1 | 실행 정체성 | 새 실행이 없다. 대상 파일 정체성 = 부록 A 파일 sha256(K-2). 도구 sha = 감사·판정 JSON·파일(K-0). 행별 `git_at_start.head`·태그는 기록한다(판정 조건 아님) |
| 2 | 부분 기록 | `{"error": …}` 블록, `restored_from`, 키 결측을 K-3으로 막는다. 메타 키가 빠져 행이 조용히 빠지는 일은 K-1(목록 sha 재현)과 K-2로 막는다 |
| 3 | 짝 없는 키 | 짝 비교가 없다. S-Ch gateoff/gateon 짝은 같은 LOC 두 행으로 따로 세고, 고유 LOC 수를 함께 적는다. 같은 `case` 여러 배치도 행마다 센다(3.2절) |
| 4 | 0건 통과 금지 | MUST `OK` 0건 = `판정 불가`. PATCH `OK`+`BLOCKED_MISSING` 0건 = ② 거짓. 기지 행만으로 ②가 참이면 공개한다(6.1) |
| 5 | 공개 항목 | 1절(봉인 전에 본 것, 기지 3행), 2.5절(스캔 도구와 출력 범위), 판정서에서 봉인 뒤 판정 전에 본 것, 재집계 중 맞춘 항목 |
| 6 | 정확한 사건 이름 | `split(":",1)[0]` 정확 일치. `_SKIPPED` 접두어 함정 시험(10.1 #5) |
| 7 | 정수 주기 비교 | 4.1절, 같은 주기 토양 모드 시작 제외(4.4) |
| 8 | 복원 불가를 추정으로 메우지 않음 | `UNRECOVERABLE`은 재구성하지 않고 등급에 반영한다(6.2) |
| 9 | 규칙 뒤 변경 금지 | 문턱(dP > 0, ≤ 0, `THIN_MARGIN` 12)을 결과 뒤 바꾸지 않는다. 바꾸려면 rev 판과 사유를 공개한다 |
| 10 | 태그 전환 조용한 실패 | 9.2 소비자 표, `endswith("_LAS")` 함정, 전환 전 재현 러너 4개 |
| 11 | 이름 혼동 | K1 세 뜻 구분(0절 규약), CLAUDE.md 문구(9.6) |
| 12 | 두 경로 | 10.1·10.2, 출처 우선순위를 달리함, K-9 완전 일치 |

## 12. 한계

- **제어기 차이**: A 74행 가운데 LAS-b가 켜진 행은 S-Ch 2행(패치)뿐이다. MUST 후보는 모두 LAS-b 전 제어기(`final_SGS_R4`·`final_C4G2`)다. 채택 대상 프리셋은 LAS-b 위의 K1이다. LAS-b는 가벼운 다리가 있을 때 이륙 접근을 늦춘다. 그래서 $t_P$가 늦어질 수 있다(dP가 커지는 쪽). 토양 모드 시작도 늦어질 수 있다. 같은 패치 키에서 옛 제어기와 LAS-b 제어기가 모두 −20이었다는 것이 유일한 근거다. 이 차이는 판정서에 한계로 적는다.
- **그림자의 범위**: 관문 꺼짐 실행에서 R4를 평가한 LOC만 본다. K1이 첫 LOC에서 막고 그 LOC가 뒤에 취소되면, 다음 LOC에서 R4가 다시 평가될 수 있다(틈 목표가 아직 없으므로). 관문 꺼짐 실행은 그 경로를 보여 주지 않는다. 이 경로는 R4c30이 늦게라도 켜지는 쪽이라 MUST 판정을 나쁘게 만들지 않는다. 그러나 확인하지 않은 경로다.
- K1이 막았을 때의 행정·크롤러 틈·READY 변화는 이 규칙에서 보지 않는다. MUST에서 막지 않음을 확인하는 것이 목적이다. PATCH에서 막을 때의 효과는 S-Ch(−29.9 mm 행정, 틈 −30 mm, E-6형 통과)가 근거다.
- 오거 중·하단, 경사, ×1.1·1.2, 잡음 등급은 A에 있는 만큼만 본다(부록 A). S1 균일은 A에 없다(B에만 있음).
- 하네스 근거와 Chrono 근거가 어긋나는 원인(4.2 해석)은 이 규칙에서 분해하지 않는다.

## 부록 A. 판정 집합 A (74행)
- 정규 목록 sha256: `2e7a1a5f70231e4662fbb985aa8e50c3983d6788bfb889800b27a086457aa9d2`(4.3절 정규형)
- 열: 경로는 `07_results/` 기준. 바닥 분류는 2.2절 규칙(인자만). 패드 B = `dwg_rear250`, A = `cad330`. 경사는 `floor_roll`/`floor_pitch` [deg]. 태그는 `args.expect_controller`(없으면 -)

| # | 경로(배치/행) | 바닥 분류 | soil | patch | 패드 | 오거 | 경사 r/p | 질량 | F_s [kN] | 태그 | result.json sha256 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `batch_COUPLED_eta085_20261104_142213/P3b_J1_B_top_Fs4` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `c75f0757703c052a07827e8b2b840d81fccdaf85849f416614681a047eca2bb3` |
| 2 | `batch_COUPLED_eta085_20261104_142213/P3b_J2_B_top_Fs4_m1p1_t180` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_SGS_R4 | `7764a72970f57423b4b6a6b67b51457498fbfac6152c199a128bb518ba21bdf9` |
| 3 | `batch_COUPLED_eta085_20261104_142213/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `676c629398c76dbe5fbf07ffb367eab828b92b942f0ab2392c3fbf0d8e98e713` |
| 4 | `batch_D1-CHRONO_20261108_131710/D1S_G1_B_bottom_Fs4_spJ1FL` | PATCH | G1 | FL:J1 | B | bottom | 0.0/0.0 | 1.0 | 4.0 | final_C4G2_P3 | `17ea55398bc54c397f3a6baadfc5a74f4307a6e7ace067a69797c608b9959088` |
| 5 | `batch_D1-CHRONO_20261108_131710/D1S_G1_B_middle_Fs4_spJ1FL` | PATCH | G1 | FL:J1 | B | middle | 0.0/0.0 | 1.0 | 4.0 | final_C4G2_P3 | `1be0887e9f89eb717073deca0e6425139fd7d124e6bfd28da93e9deeb38d9e2a` |
| 6 | `batch_FINAL-C4G2_20261105/P3b_J1_B_top_Fs4` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `6eed70601355b11286ec0ed5b07748de686d0e74edd1bdae4eb132a3c22fe0c3` |
| 7 | `batch_FINAL-C4G2_20261105/P3b_J1_B_top_Fs4_m1p1` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `c1a04adde15382daff0ba156254f3d355e29680b4a59d84cd248858ff464c0c3` |
| 8 | `batch_FINAL-C4G2_20261105/P3b_J2_B_middle_Fs4` | UNIFORM_SOFT | J2 | - | B | middle | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `d75c7369ee61c647a977c8516c4d8546e0c25f7d750adde4b4e9c5004dc980c5` |
| 9 | `batch_FINAL-C4G2_20261105/P3b_J2_B_top_Fs4` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `b74d5f400a7d920ded10b0e62f0bd06f9118d09e3a717abc988c97e3882b5943` |
| 10 | `batch_FINAL-C4G2_20261105/P3b_J2_B_top_Fs4_m1p1` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `42073e8bcdcf0ecf165705d356032784dd4934a2d0c538d5564ed50c6372c037` |
| 11 | `batch_FINAL-C4G2_20261105/S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0` | UNIFORM_SOFT | J1 | - | B | top | -2.86/0.0 | 1.0 | 4.0 | final_C4G2 | `25eb2ea064afbb1cc7e6e970f1b0dd276e9858f841f0803b819ff93bdd5119c8` |
| 12 | `batch_FINAL-C4G2_20261105/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_C4G2 | `fbd4413c35369979abcc28f307bfe563a299ca06b1ec9dd164f47adda0da9947` |
| 13 | `batch_FINAL-REP-X_20261031_020716/P3b_J2_B_top_Fs4_m1p1_t180` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_SGS_R4 | `18875c14c020d7e0f0412381e4a25457f97489340a7efa5cde12266ce2bc3fd7` |
| 14 | `batch_FINAL-REP_20261030_223359/P3b_J1_B_top_Fs4` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `26424a7d105a0c237f342ade5675305ca39f4d145624fe0f034990b67ab11c0e` |
| 15 | `batch_FINAL-REP_20261030_223359/P3b_J1_B_top_Fs4_m1p1` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_SGS_R4 | `0a0f6fd351731826b8015174f418699d5b354ee3b0ca2967f61741fc05defa70` |
| 16 | `batch_FINAL-REP_20261030_223359/P3b_J2_B_middle_Fs4` | UNIFORM_SOFT | J2 | - | B | middle | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `c2377d8f6c1491d0714d458525fe0a9022eaec3cb666f80faf79c99a835b3abf` |
| 17 | `batch_FINAL-REP_20261030_223359/P3b_J2_B_top_Fs4` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `36e2220eae7a5762b4895f90f7a2ca9f4cf32869098d0a230897617e60ae8c59` |
| 18 | `batch_FINAL-REP_20261030_223359/P3b_J2_B_top_Fs4_m1p1` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_SGS_R4 | `2d84ce62d3013923ca9dabee8ba726ddf7292cd18d04ec583376bf178e8bca13` |
| 19 | `batch_FINAL-REP_20261030_223359/S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0` | UNIFORM_SOFT | J1 | - | B | top | -2.86/0.0 | 1.0 | 4.0 | final_SGS_R4 | `9813384030a074d3b717e604c19790e2b5ed6ef4476a6a6d46b469b78f5182dc` |
| 20 | `batch_FINAL-REP_20261030_223359/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `d121d7c118044a7e6d35446c2c1c62c01cec4d756ef20764fd348f1adadd1063` |
| 21 | `batch_FINAL4_20261102_060540/G6_G1_B_top_Fs4_spJ1RR` | PATCH | G1 | RR:J1 | B | top | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `68d648df0d2862ce1c9a8b5575da9f7f7c1a722b1323d721b01987f4e93d43f9` |
| 22 | `batch_FINAL4_20261102_060540/G6_G1_B_top_Fs4_spJ2RR` | PATCH | G1 | RR:J2 | B | top | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `2969e6a42bcf368f2924c5465beb464c7fc2e24fa3f73167d3150e784768f891` |
| 23 | `batch_FINAL6_20261031_000833/P3b_J2_B_top_Fs4_sgRRd150` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `0f03dc6baf2ef5584d52ff4b13015f27015983dd7f0359cc78900adc688462e5` |
| 24 | `batch_JOURNAL-AUGER_20261031_165543/P3b_G1_B_bottom_Fs4` | UNIFORM_G1 | G1 | - | B | bottom | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `b3bb937145821c5d1852c662ef17ef245fef556d62072272a60c3887a567e95b` |
| 25 | `batch_JOURNAL-AUGER_20261031_165543/P3b_G1_B_middle_Fs4` | UNIFORM_G1 | G1 | - | B | middle | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `f2644d0adedd6e863d4fd2210aed7192eb2af3536224d366d10a3461ecfb4869` |
| 26 | `batch_JOURNAL-AUGER_20261031_165543/P3b_G1_B_top_Fs4` | UNIFORM_G1 | G1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `7823156a9983314928b628e6a15f05a477c141a339870c293b9acea5de79abf1` |
| 27 | `batch_JOURNAL-AUGER_20261031_165543/P3b_J1_B_bottom_Fs4` | UNIFORM_SOFT | J1 | - | B | bottom | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `6598829a6401c9422cfd137c1f4b0953b2fc69b4dd39b87aba40dca0dd049fbe` |
| 28 | `batch_JOURNAL-AUGER_20261031_165543/P3b_J1_B_middle_Fs4` | UNIFORM_SOFT | J1 | - | B | middle | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `74befef1c6548841aae934e56404444ca3cff85f15660b4848079bd7ea19e6f5` |
| 29 | `batch_JOURNAL-AUGER_20261031_165543/P3b_J2_B_bottom_Fs4` | UNIFORM_SOFT | J2 | - | B | bottom | 0.0/0.0 | 1.0 | 4.0 | final_SGS_R4 | `c2309a13a9f2eb5723b669f84b2710319c5e1bdb01d713b5e34204d5886cbd21` |
| 30 | `batch_RV6_20261031_025137/S9SL_X6rb_J1_B_top_Fs4_rm2p64_p0` | UNIFORM_SOFT | J1 | - | B | top | -2.64/0.0 | 1.0 | 4.0 | final_SGS_R4 | `fc370f426f6513d246e42c6a1c3752475fa714b454f69b1ea3293e10855af8fe` |
| 31 | `batch_RV6_20261031_070613/S9SL_X6rb_J1_B_top_Fs4_r2p64_p0` | UNIFORM_SOFT | J1 | - | B | top | 2.64/0.0 | 1.0 | 4.0 | final_SGS_R4 | `a2b79fd664c3360a856d55ef26c7bb1177d1315d05a7df130604a25bc01f4d2b` |
| 32 | `batch_RV6_20261031_091226/S9SL_X6rb_J1_B_top_Fs4_r2p2_p0` | UNIFORM_SOFT | J1 | - | B | top | 2.2/0.0 | 1.0 | 4.0 | final_SGS_R4 | `2725a46024b855776a9d506f34804321ed28599ad90c95cdfd6a3c65c071fed4` |
| 33 | `batch_V5-LAS-K1-CHRONO_20261109_193952/SCh_G1_J2FL_B_top_Fs4_VB_gateoff` | PATCH | G1 | FL:J2 | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2_P3_LAS | `7f2adafb8f429806e3bcf8bf23516e49dd96ee71f7f49777e184cbe04db93767` |
| 34 | `batch_V5-LAS-K1-CHRONO_20261109_193952/SCh_G1_J2FL_B_top_Fs4_VB_gateon` | PATCH | G1 | FL:J2 | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2_P3_LAS | `115d8713c34c6f19490119d7a258cc75dff8767af86439892bfbce4690dfaa8f` |
| 35 | `batch_V5-PROBE_20261106/b5_base` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `38becc6a14c0ab63b0b64e2acb8f35745916875dbb957b7534bab1f69a9ed761` |
| 36 | `batch_V5-PROBE_20261106/probe_flow` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `d62d24b2be36d5920cdb18b6d4c0a5a4b873e059e8e5bdcad6609df97793f616` |
| 37 | `batch_V5-PROBE_20261106/probe_valve_m2` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `ca43338364acf1fc679bb560e203741e15967750cd0f2d088038f87b3310134a` |
| 38 | `batch_V5-PROBE_20261106/probe_vb` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `b2e66f8d211d837bba8d314016df629bfebefac20e9adacd3fb06e8910428c30` |
| 39 | `batch_V5-PROBE_20261106/probe_vb_m1c_vn` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `024e0bd8114e384b9ade6a7811cc497dbe706b94336c52bc3b73bc50eb9d8d12` |
| 40 | `batch_V5-PROBE_QUIET_20261107/probe_vb_quiet` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `16dec94f35fa991a7f4bbf1448d02a8722bcfb4fd25df7c521196872860668cb` |
| 41 | `batch_V5-STAGE3_20261107_184239/P3b_J1_B_top_Fs4` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `7552e298322a1fd36a0aa1c4034e4a5c2798e0ba16644007af4b231cf448a383` |
| 42 | `batch_V5-STAGE3_20261107_184239/P3b_J1_B_top_Fs4_v0v` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | final_C4G2 | `53c5f1fe599550d80a03b35cbfc099ca676aed79c135d31c6a0f57cbb62895b6` |
| 43 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `20cecb240c8c0a4ace82b88462ce2d11345983a12c62de9a9d3e44abab741e6f` |
| 44 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180_seed20261026` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `818a9da2379d29303f25f0b8a07c1479eaeb696190bf127acd2f763543e9648c` |
| 45 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180_seed20261026_flow` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `77200b3b2126f96f3e98e0b0e04f02c764bdf434d23e5640d63d54d742cfc876` |
| 46 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180_seed20261027` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `99ecb10254f6049c5e3866e272caedfd9cda477b7c9768b05a0e4d8acaa6eac4` |
| 47 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180_seed20261028` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `ed51ed280679f1c65ed1f0ddc27c7f18385cdd200b2faafb401ce0d232c7f417` |
| 48 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180_seed20261029` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `22eb08c7fc52e79de053921f2e4a82f8b2c9491bf518a3eba1598a0c669f25d6` |
| 49 | `batch_V5-STAGE3_20261107_184239/P3b_J2_B_top_Fs4_m1p1_t180_v0v` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | final_C4G2 | `3a895d6961e31f2034b92a71f4d48e2f27e678eaaac72df99bf956fcd073db7b` |
| 50 | `batch_V5-STAGE3_20261107_184239/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_C4G2 | `38c67199f4c3607af492b3a40f43f8f5ae65a8064ae85885f57e7921f073dcce` |
| 51 | `batch_V5-STAGE3_20261107_184239/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0_v0v` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_C4G2 | `ab5f8bfecc28d69aabee1b649da454bf19da6fcda07c78498fa951b5fd125c36` |
| 52 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_RE1bF_d001_off` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `ce26df29b29b9c7e5c19b0b3fa08d18cfc715f78eb58a1c149b1bac21df0df3e` |
| 53 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_RE1bF_d003_C4G2` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `7759f7b3e1e61d4c2379921f9b656b3a4159ee3b2a8fb423c4da3fb8e5ef1cbf` |
| 54 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_RE1bF_d003_off` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `4e2b1d8135118f30c9db5deedca5c2e3ba7138e4dbe83080250f14260b0c6edc` |
| 55 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_RE1bF_d005_off` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `f8b28c7a94ddc82600a7774e1101ba935623f946e9e7b2342335219f115632eb` |
| 56 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_RE1bF_d007_off` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `a81c707d3c9f44be2d9140f12a2216229268541184b4b286bd42b2b76130f91b` |
| 57 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_RE1bF_d009_off` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `bd2e6f1ff6d793e5487d5caacff29c3382ad07aa7b04baf3602d12bf2b1ed26a` |
| 58 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_RE1bF_off` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `a06676b7adfdce523e5ce48b6c2966a8bc930f16088921ffb750f825f3a22a68` |
| 59 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_RE1bF_on` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `8fe8bb5c9653789682def05c3a5771c2a56d1ba312b9a44c1cf4c264f1d8d674` |
| 60 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs0_base` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `b8d09716dbec0a842b5dcd620d7046d90c2d52110f78c2c39503f737e16c2898` |
| 61 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs8_RE1bF_off` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 8.0 | - | `7b0fc12ec4029effc535ea73d410beccb5f50faa0fe3a596b3cb629a06106c11` |
| 62 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs8_RE1bF_on` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 8.0 | - | `c6495ddb7b0ecd7fbe81144542bf1b2c3509fd3dc13cb5f83f598465dcdc9b66` |
| 63 | `batch_k1soil_G1_20261105/S9EV_G1_FLFs8_base` | UNIFORM_G1 | G1 | FL:G1 | B | top | 0.0/0.0 | 1.0 | 8.0 | - | `f361a2354332f5c2015a7312feaae80601493b0f9d3903a14a0f30b623983e3f` |
| 64 | `batch_k1soil_G1_20261105/S9EV_G1_RRFs0_RE1bF_off` | UNIFORM_G1 | G1 | RR:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `5fedb14dbf13ddbd58902c06c848c79de519731c3c0a76f56c7840008a053e8b` |
| 65 | `batch_k1soil_G1_20261105/S9EV_G1_RRFs0_RE1bF_on` | UNIFORM_G1 | G1 | RR:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `6c40f3c59fa1ab4d5f74c937710a5c235c9552594885d6ca4a67c9938a223075` |
| 66 | `batch_k1soil_G1_20261105/S9EV_G1_RRFs0_base` | UNIFORM_G1 | G1 | RR:G1 | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `612d32a9794064d910f4413823cfbbe801b4b837aaa6fe26845c0d005a35fdf1` |
| 67 | `batch_s8_eta090_20261105/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `bb27ededbbacbd5107f0a2c3b8fbbe4ac21bcd5503c57e2ba3b8494818d8c694` |
| 68 | `batch_s8_eta0925_20261105/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `b978bdad1b1bebbb838a41f447ac5ecda7886b61a3270e2460bb187f54809e0e` |
| 69 | `batch_s8off169_e0p50e-3_20261105/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `9670a08317b260dc3757c5ab54e9be500a1dd276bbe71eb88980d1585a57a893` |
| 70 | `batch_s8off169_e0p75e-3_20261105/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `15129b79de5f9307182dbe1dd1f955243d1023056e141d93e31d64d0bed12d23` |
| 71 | `batch_s8off_eps1e-3_20261104/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `f08892706d914daacfcbd8c1ef5ffd27762b85fa2d18076c0db6ee78b428b4ff` |
| 72 | `batch_s8off_eps2e-3_20261104/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `6dc502f75a3f8e7132ae69be8807463582860becdd78b6df83beebcbfebb2ee2` |
| 73 | `batch_s8on_eps1e-3_20261104/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `6c60a3abab8276d9f7499cf03db73b120a3e24e52918bef6402e00d2f91868c2` |
| 74 | `batch_s8on_eps2e-3_20261104/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | final_SGS_R4 | `8250323b4c2884267bc3a1e91b0921ef86a4671e04264a4018ba05076f33cb04` |

## 부록 B. 보조 집합 B (43행, 기록만)
- 정규 목록 sha256: `50622923473e9b05aec58513d7a76b739a040a5cd063c519f751bc9926b561c9`(4.3절 정규형)
- 열: 경로는 `07_results/` 기준. 바닥 분류는 2.2절 규칙(인자만). 패드 B = `dwg_rear250`, A = `cad330`. 경사는 `floor_roll`/`floor_pitch` [deg]. 태그는 `args.expect_controller`(없으면 -)

| # | 경로(배치/행) | 바닥 분류 | soil | patch | 패드 | 오거 | 경사 r/p | 질량 | F_s [kN] | 태그 | result.json sha256 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `batch_D424R_20261030_073635/P3b_J1_B_top_Fs4_m1p1` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | - | `73961ded368d6ae4abb03bc39655d5a7572659846a10257d7a45ad85ffed0784` |
| 2 | `batch_D424R_20261030_073635/P3b_J2_B_bottom_Fs4` | UNIFORM_SOFT | J2 | - | B | bottom | 0.0/0.0 | 1.0 | 4.0 | - | `3f3eba81a2966c9bb17820732ce7346b68516cdc8b622bdc9f5ce7c3bcd7423a` |
| 3 | `batch_D424R_20261030_073635/P3b_J2_B_middle_Fs4` | UNIFORM_SOFT | J2 | - | B | middle | 0.0/0.0 | 1.0 | 4.0 | - | `c95e856b418aa0002679c02fe4e598932b92249b6938c9e3e0cc88e68525e774` |
| 4 | `batch_D424_20261030_014908/P3b_J1_B_top_Fs4_m1p1` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | - | `66e213c9c62702455f51630664797874271898746e2214b6d43d99e9a9e9462e` |
| 5 | `batch_D424_20261030_014908/P3b_J1_B_top_Fs4_m1p2` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.2 | 4.0 | - | `fa5f646ae529f498ff37616aeaaaa9a26729170a9817c28985f9d77b9b17a42e` |
| 6 | `batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ1FL` | PATCH | G1 | FL:J1 | B | top | 0.0/0.0 | - | 4.0 | - | `5001992eecf56054f0fdf1df75c90d098c3ae123860ac45338389e283be24a05` |
| 7 | `batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ1RR_noTR` | PATCH | G1 | RR:J1 | B | top | 0.0/0.0 | - | 4.0 | - | `5c66e6d39b0b7619175d40682e75a72d408f842759bccc33e8d0e54fbc9ab4c6` |
| 8 | `batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ2FL` | PATCH | G1 | FL:J2 | B | top | 0.0/0.0 | - | 4.0 | - | `0213225c4deea7197d41849cc2e8fc9255745b60a661039f978ee9123b1ae80c` |
| 9 | `batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ2RR` | PATCH | G1 | RR:J2 | B | top | 0.0/0.0 | - | 4.0 | - | `7c18deb6065b322b80079f011e8aa01baf4d4dc5e8dce3e8c5dd77f4b518dc0c` |
| 10 | `batch_G6P_20261029_103815/G6_G1_B_top_Fs4_spJ1RR` | PATCH | G1 | RR:J1 | B | top | 0.0/0.0 | - | 4.0 | - | `d858d3cf2a851b2d7e38881ff3084da5a9b07b87c59f93819eac1f00e1067fbd` |
| 11 | `batch_G6P_20261029_103815/G6_G1_B_top_Fs4_spS1FL` | PATCH | G1 | FL:S1 | B | top | 0.0/0.0 | - | 4.0 | - | `2e59fe74f1545387a2ee053f7c732e452dbd8ef8f1f3bd0103dc7cab6d8a865b` |
| 12 | `batch_G6P_20261029_144418/G6_G1_B_top_Fs4_spS1FL` | PATCH | G1 | FL:S1 | B | top | 0.0/0.0 | - | 4.0 | - | `eb1a666493c2456bf5f69605f0bc2115c9f83b488a7f24be9c8e7df6355726ed` |
| 13 | `batch_G6_20261028_075108/G6_G1_B_top_Fs4_spG1RR` | UNIFORM_G1 | G1 | RR:G1 | B | top | 0.0/0.0 | - | 4.0 | - | `08219e800324a36cb46d73ceb586c92f83f70099af7b50e16b5867637c68c0a8` |
| 14 | `batch_G6_20261028_075108/G6_G1_B_top_Fs4_spJ1FL` | PATCH | G1 | FL:J1 | B | top | 0.0/0.0 | - | 4.0 | - | `a1fe8d3d3811ac084e2a4140771275c53dab45cd8b6f6bfb2c8d225c9a7ccb29` |
| 15 | `batch_G6_20261028_075108/G6_G1_B_top_Fs4_spJ1RR` | PATCH | G1 | RR:J1 | B | top | 0.0/0.0 | - | 4.0 | - | `5afea65d23228b4fbcda41b1fc6d7e0345ac39fb16c8d11776fb7bcdb0a123dc` |
| 16 | `batch_MS1_20261029_183324/P3b_J1_B_top_Fs4_m1p1` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | - | `8804413c9bd87d34dad56fae34fd337aa30e1fba9adfc1a877cde438c2c6e151` |
| 17 | `batch_P3b_20261027_174330/P3b_J1_B_top_Fs0` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | - | 0.0 | - | `36952f732ace550d855e6d8f557331ed00153f5014ff6d5ee52b01a54eb621b2` |
| 18 | `batch_P3b_20261027_174330/P3b_J1_B_top_Fs4` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | - | 4.0 | - | `aa69020c76f8b13179a7648060a066b6b8779a42483ca5ece08ac225c7dc8699` |
| 19 | `batch_RV1_20261030_111615/P3b_J2_B_top_Fs4_m1p1` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.1 | 4.0 | - | `b3db804ce649931597d63f37731b7050e150ffa811c26ff33910f26ac483ca72` |
| 20 | `batch_RV1_20261030_111615/S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4` | UNIFORM_SOFT | J1 | - | B | top | 1.925/1.4 | 1.0 | 4.0 | - | `6b935b54b499abee57ff2c38e51cdfb76fc0fdb1a6b43de58461726ec71832bf` |
| 21 | `batch_RV1_20261030_111615/S9SL_X4nd_J1_B_top_Fs4_r0_p2p8` | UNIFORM_SOFT | J1 | - | B | top | 0.0/2.8 | 1.0 | 4.0 | - | `5062d9d5ff59e316d00686870e8ddb2ff0b2c04e0282e9ac3fca52aea5d815d8` |
| 22 | `batch_RV1_20261030_111615/S9SL_X4rp_J1_B_top_Fs4_r3p85_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.85/0.0 | 1.0 | 4.0 | - | `0624dad95e6e138bb31564a9bd7acc5128ef1359d09533eaca48736d4df68b07` |
| 23 | `batch_RV2_20261030_154549/P3b_J1_B_top_Fs0` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 0.0 | - | `b5ba074667589804132e00c240512dbfb4d9fdf3b2e7d9f5a666d25070a0c1e7` |
| 24 | `batch_RV2_20261030_154549/P3b_J1_B_top_Fs4` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | - | `a31414f904fc0268b2494dbf3234ca12f9d4c07e97efbe6218a5077fd7880573` |
| 25 | `batch_RV2_20261030_154549/P3b_J1_B_top_Fs8` | UNIFORM_SOFT | J1 | - | B | top | 0.0/0.0 | 1.0 | 8.0 | - | `ada4937eea8f390837712f221e6fe6219e87eb0706ab3a52c20c9e28ade33ec9` |
| 26 | `batch_RV2_20261030_155059/P3b_J2_B_top_Fs4` | UNIFORM_SOFT | J2 | - | B | top | 0.0/0.0 | 1.0 | 4.0 | - | `a4e61ae45d73b444b725796a79c8e6eea57ae629a1eada05c1e851052e1242de` |
| 27 | `batch_RV3_20261030_134001/S9SL_RV3B_S1_B_top_Fs0_r3p3_p0` | UNIFORM_SOFT | S1 | - | B | top | 3.3/0.0 | 1.0 | 0.0 | - | `b8eb479ee3c7830171053fa315ed85f05df86595c2ac77bb1ded283ed5da97a5` |
| 28 | `batch_RV3_20261030_134021/G6_G1_A_top_Fs4_spS1FL` | PATCH | G1 | FL:S1 | A | top | 0.0/0.0 | 1.0 | 4.0 | - | `4351dfc1e1c92e2f596ae2daa9a77b1170e5749248ee910a5e9246d0cb8e74cb` |
| 29 | `batch_S9SL_20261028_191152/S9SL_C4_J1_A_top_Fs4_r0_p3p2` | UNIFORM_SOFT | J1 | - | A | top | 0.0/3.2 | - | 4.0 | - | `db604d15cff5afa6e55b408c149e7eb4bb702a5f27576f1da63dc3da080c02a8` |
| 30 | `batch_S9SL_20261028_194403/S9SL_C2_J1_A_top_Fs4_r4p4_p0` | UNIFORM_SOFT | J1 | - | A | top | 4.4/0.0 | - | 4.0 | - | `5fcca1e001affb3747161d27d7f66b12165b960a3c1936a3bed82a199376e0b1` |
| 31 | `batch_S9SL_20261028_223348/S9SL_C3_J1_B_top_Fs4_r3p3_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.3/0.0 | - | 4.0 | - | `f9f46a43b06148c498a10754c93215eeb1e914fe02171915197fb136eaf71687` |
| 32 | `batch_S9SL_20261029_144406/S9SL_C1_G1_B_top_Fs4_r0_p3p2` | UNIFORM_G1 | G1 | - | B | top | 0.0/3.2 | - | 4.0 | - | `864a746ca4f3cd3be1da970e6b393a33138ee3ada43ce958c07472a2aaf9ea64` |
| 33 | `batch_S9SL_20261029_144406/S9SL_C2_J1_A_top_Fs4_r4p4_p0` | UNIFORM_SOFT | J1 | - | A | top | 4.4/0.0 | - | 4.0 | - | `98a7a75941462c130d9146c096f0a41b3df199040ba960965d384f8169182ebc` |
| 34 | `batch_S9SL_20261029_144406/S9SL_C3_J1_B_top_Fs4_r3p3_p0` | UNIFORM_SOFT | J1 | - | B | top | 3.3/0.0 | - | 4.0 | - | `cdd3a704737b0f95deb0c55ae7a7d60134fd5fec9a9ec2a9dc529088e8db0e60` |
| 35 | `batch_S9SL_20261029_144406/S9SL_C4_J1_A_top_Fs4_r0_p3p2` | UNIFORM_SOFT | J1 | - | A | top | 0.0/3.2 | - | 4.0 | - | `e4cbbba35382d1a974fe2e0a6c237d3e5b9edfda54dd6892cbc4532256a7426f` |
| 36 | `batch_p3b_aug_20261028_224127/P3b_J2_B_middle_Fs4` | UNIFORM_SOFT | J2 | - | B | middle | 0.0/0.0 | - | 4.0 | - | `5fcd1582506804c88e5e98d8cbd969f3b530123116427be65e6eaacb3942e775` |
| 37 | `batch_p3b_aug_20261029_002839/P3b_J2_B_bottom_Fs4` | UNIFORM_SOFT | J2 | - | B | bottom | 0.0/0.0 | - | 4.0 | - | `ba9ae7e9920051b5be4738bae2cbbe61a51e4e0f6cd770941715edfcb9470a67` |
| 38 | `batch_p3b_aug_20261029_103815/P3b_J2_A_bottom_Fs4` | UNIFORM_SOFT | J2 | - | A | bottom | 0.0/0.0 | - | 4.0 | - | `6fc767a926211fdae00cc30ef8b1bc169c1fd132016d33f8c87961d0cbc8a16a` |
| 39 | `batch_p3b_aug_20261029_103815/P3b_J2_A_middle_Fs4` | UNIFORM_SOFT | J2 | - | A | middle | 0.0/0.0 | - | 4.0 | - | `3f099cbd90f5d56a8748cd4da30488e7ca3b97e37b0f6256a8934475dcead571` |
| 40 | `batch_p3b_aug_20261029_103815/P3b_S1_A_bottom_Fs4` | UNIFORM_SOFT | S1 | - | A | bottom | 0.0/0.0 | - | 4.0 | - | `1fd690e39f6a24d805a1577e9aa0ce483c5ed09d2466502816e55eb1b44bfe15` |
| 41 | `batch_p3b_aug_20261029_103815/P3b_S1_A_middle_Fs4` | UNIFORM_SOFT | S1 | - | A | middle | 0.0/0.0 | - | 4.0 | - | `b0f614606974456eb057d1c29d0ba9328b5371f7b58876fd3fc65c26a0f6da89` |
| 42 | `batch_p3b_aug_20261029_120112/P3b_S1_B_bottom_Fs4` | UNIFORM_SOFT | S1 | - | B | bottom | 0.0/0.0 | - | 4.0 | - | `80204f096b03f8cde622afbe620485cc63638836d198a7f95547f310adde1dd4` |
| 43 | `batch_p3b_aug_20261029_120112/P3b_S1_B_middle_Fs4` | UNIFORM_SOFT | S1 | - | B | middle | 0.0/0.0 | - | 4.0 | - | `5b7f0688e8a42a6e236f4d01c87c9e77303f2d629dcbf8b6b474b3617ca9d297` |

## 부록 C. 제외 집합 E (183행)

- 정규 목록 sha256: `ae171b438318ada7a128adc26885a869d34345080fa6a99f362467a5d73bd473`
- 형식: `사유<TAB>경로<TAB>sha256`(경로는 `07_results/` 기준)

```text
not_run_S9_level	S9/batch_DT_20261026_122444/DT_G1_B_top_M14s_dashpot8s_dt5e-5/result.json	066f2977e1a3558b86e948edc4877be162b8154ae2387e7d9af6900a08f7c471
not_run_S9_level	S9/batch_DT_20261026_122444/DT_P3a_G1_B_dt5e-5/result.json	811ce6b4b808a671cff18d6d088a747c6957e5c7ca9404d9dbc7c688ff540749
not_run_S9_level	S9/batch_FINAL-C4G2_20261105/hash_check/G1L_RE1bF_FL_top_Fs0/result.json	09c16998fded4ff985e4d67f2bed9ef68b4f7d274d986ffd7daaacd49db944bb
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_A_bottom_rpB_Fs0/A_bottom_rpB_Fs0/result.json	2ad2393f7129073b089b759d0ee0f6607b14e57a816035f6388e2848c3e0d53e
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_A_middle_rpB_Fs0/A_middle_rpB_Fs0/result.json	80b63e123682089768f0ac973e07c4f267abc3093540d10318440339e2a2f859
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_E_G4_Fs4/E_G4_Fs4/result.json	d7e52d8bc3e5abca8f5f6a0f4f0a7352ff7609a1002445fc19285271b5fdbd05
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_E_RE1bF_Fs8/E_RE1bF_Fs8/result.json	8976e4069ffdafe6b5ea27399882f2b59f37e9603b85c95736003eb6f2ac0a61
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_E_SS_Fs4/E_SS_Fs4/result.json	174732632f315fd51d0c8fcf026e5e9d8502902928465b06b21a80ab6a9b92db
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_G1L_RE1bF_FL_top_Fs0/G1L_RE1bF_FL_top_Fs0/result.json	7bc055b8352fefd7a4339bf4a8c18c348b007bdcc66a32e22f4a4819c364151c
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_G1L_RE1bF_FL_top_o050_Fs4/G1L_RE1bF_FL_top_o050_Fs4/result.json	a03f57f92183fb263196331a9db7164fabeec412097c96f3a732a8d1afa198b1
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_G8C1_top_edge_FL_g170/G8C1_top_edge_FL_g170/result.json	ef68e9cc52ea56c3be9875f16e2c19c85acf6f188e85150e7dd35377f1badb41
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_G8C3_top_edge_RL_g230/G8C3_top_edge_RL_g230/result.json	f6ddd448ad53222c8a5dec0c7ef728b26e6f47c8400e66f30820646b784c0f8a
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_K0V_top_rpB_Fs0/K0V_top_rpB_Fs0/result.json	49e5387882d812028a4187c0d9070cd0c7708fa7b04f8362011d340878f19ad1
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_K24_top_fdown3.5_Fs4/K24_top_fdown3.5_Fs4/result.json	6b4fd9911dacad2e5d6a0b4414714905a926bfc1430f1a0304f540304444da23
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_K24_top_flat_Fs4/K24_top_flat_Fs4/result.json	e1f2d62f9d1e206e7e99310b0fe158a6f0f7ac78fff47760f482c3338dd3af8b
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_K24_top_fup3.5_Fs4/K24_top_fup3.5_Fs4/result.json	4b429ecae01e23036e09502cb44d531a6853e4b99374349b6faf8f0762a6c003
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_K24_top_roll5.5_Fs4/K24_top_roll5.5_Fs4/result.json	9864aac00abeedb8327775034f1dcbaa50e1603b63c85f007797c6d7c3b3e805
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_K24_top_rpB_Fs4/K24_top_rpB_Fs4/result.json	141dd07cd534817ae93bc204e94bb56350bbeec3613c2d077f2e5171e5268640
not_run_S9_level	S9/batch_FINAL-R-C4G2_20261105/final_K8_top_rpB_Fs8/K8_top_rpB_Fs8/result.json	b6ea080efcfb86ad031918304fcad3122f0f268c85616d42bffc9fb6ec13198f
not_run_S9_level	S9/batch_G6_20261028_075108/G6-0a_G1_B_lift_spG1RR/result.json	f51b4f19bf834b98c662f106367f0e7c472ef69cc3ffb8e5bbd8f00f82d17a2e
not_run_S9_level	S9/batch_P1_L_20261026_034511/L1_G1_fixed_F0_bprime_2cm/result.json	e63ce27954858fa24cfb08d14abd262801679674ccc29c3b8b521386ece4c3ce
not_run_S9_level	S9/batch_P1_L_20261026_034511/L1_G1_fixed_F0_native_2cm/result.json	028f44a48b8e97f3ba97f98fcc7843bc6675ddd0f345f1964d588fa4281ee40d
not_run_S9_level	S9/batch_P1_L_20261026_034511/L1_J1_fixed_F0_bprime_1cm/result.json	f8b3adfe181a1290f6dd2f1925c139b1b46802dd0e005bd51c7c5339b238ad64
not_run_S9_level	S9/batch_P1_L_20261026_034511/L1_J1_fixed_F0_native_1cm/result.json	64d6340b1b5df6521f3fb9722d61dd38e2394b10fc54ba2279235d2724356463
not_run_S9_level	S9/batch_P1_L_20261026_034511/L2_J1_B_RL_F20000_1cm/result.json	e668c5a454406450bc4d31dd54cd20504cd77bc155489a335daa8df8b7b0e46a
not_run_S9_level	S9/batch_P1_L_20261026_034511/L2_J1_B_RL_F4450_1cm/result.json	c54d766a23983475a5c4e6b0c63794c0148eb4492dcecf763e88e590d190b531
not_run_S9_level	S9/batch_P1_L_20261026_034511/L2_J1_B_RL_F6980_1cm/result.json	2b4f8a1aa0f83470dc058724e54d1939cfe8ed90dfa77deda2b32768fa14fc35
not_run_S9_level	S9/batch_P1_L_20261026_034511/L3_J1_B_RL_1.2limit_1cm/result.json	e07537a821622b85a3632c4056d19a5627252464696dd7f0b2e5eb006ac34219
not_run_S9_level	S9/batch_P1_L_20261026_034511/L3_J2_B_RL_1.2limit_1cm/result.json	1bcedeb304698d97e19cfe5770b455151e50f6fecfb3fc0c3e3d37642c76e66b
not_run_S9_level	S9/batch_P1_L_20261026_034511/L4_G1_B_RL_2cm/result.json	e89f1a5a2e37e1069fe0ff0f471e143f6f0e628a6bf0b2b0c715c09ea9ead235
not_run_S9_level	S9/batch_P1_L_20261026_034511/L4_J1_A_FL_1cm/result.json	405ab78c1b8cc061d5d2baa2cba97486cd311888404cd654d874cb59d7996ca2
not_run_S9_level	S9/batch_P1_L_20261026_034511/L4_J1_B_RL_1cm/result.json	f846d1be24880e2776c0e193cc464b2093986f46c1a4d83d6e971774db49284e
not_run_S9_level	S9/batch_P1_L_20261026_034511/L4_J1_B_RL_1cm_ksw0/result.json	c8a18a616f70baf79b25829da4c0f99dd5a146fe3daefd36170d26a1558b5334
not_run_S9_level	S9/batch_P1_L_20261026_034511/L5_G1_M14s_pitch3.5/result.json	2b8ade31f585ccc17800b7894bf4bb6ed51b3291ec457694f6c7dddfda818ad8
not_run_S9_level	S9/batch_P1_L_20261026_034511/L5_J1_M14s_pitch3.5/result.json	8439b11af5ac906a7c2cfe05d2834877f3f0e9a9882dffda109aca8e6d29a0ea
not_run_S9_level	S9/batch_P1_L_20261026_034511/L6_J1_B_RL_native_fixed_dt1e-4_1cm/result.json	26dfb1ea287064be95d7ea4ad930009e95d783400b1b70cb8846810c0f6b3dea
not_run_S9_level	S9/batch_P1_L_20261026_034511/L6_J1_B_RL_native_fixed_dt5e-5_1cm/result.json	7be04eb2c5355e88d12152cab47a7bcf1354d8eb54063b7ce2eefa4095a7f6fa
not_run_S9_level	S9/batch_P1_L_20261026_034511/L6_J1_B_RL_native_spherical_dt1e-4_1cm/result.json	47c46570ce26326bd4fcf320616ea72dc87740a9c54319eecc4c0b8f866ebb6d
not_run_S9_level	S9/batch_P1_L_20261026_034511/L6_J1_B_RL_native_spherical_dt5e-5_1cm/result.json	e39b77dedbb24620e22dd7642f7c9e9ef415fdcdfe42759bfc8294091efea421
not_run_S9_level	S9/batch_P1_V0p_20261026_030143/V0p_G1_B_RL_0p5cm/result.json	d2fa61151f2b8e5985ce158805155279f10ce6b7d8b4fe6b944bac1b24983810
not_run_S9_level	S9/batch_P1_V0p_20261026_030143/V0p_G1_B_RL_1cm/result.json	b32fdf61adc217ddd8241f757d2bf9daf177f7ae3573205fac846dd7520e9d82
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_G1_B_FL_0p5cm/result.json	603654072612d4d523c8fc35a11fc38b18b48fed9af1410647dc67b40f465eaf
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_G1_B_FL_1cm/result.json	9eaacf90ae7b454677b35548a6868c9e3dbf9732d5e847eb8e5545655ab207dd
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_G1_B_FL_2cm/result.json	9a2594665ab62cdb9e8a2861f75ee3689a21dc04729443aee80d0a3c89b04d77
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_G1_B_RL_0p5cm/result.json	37c86074298a1d3439f5338f47ec5b19cfff406ee08a2c45dbd0c56ec4f223ef
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_G1_B_RL_1cm/result.json	c62ac720f85d1e070ba17de1f38e7bfe59d2d1afd7da4ba3f014b86614f1e660
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_G1_B_RL_2cm/result.json	f1e6dba6231c4509820e2390d004a2adb26a00a7fe2c2c65d0f1a4879fd843a8
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_J1_B_FL_0p5cm/result.json	726d7f3e81b550f3bb82a8cad20f80e27f0ffc68accfa249256af8c7e28cb0d7
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_J1_B_FL_1cm/result.json	46429be93314217c2f3be582184bf26a641022e999a4b4aa0bf684b40f6fa144
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_J1_B_FL_2cm/result.json	f1b123c49b0e73abccddd98ce4ea0a3f9bc27c31b202c9d8733edcf79e4309d4
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_J1_B_RL_0p5cm/result.json	63831025eff12f9d9fc9215f42b0ff179c883cc61aff0a2678036a62f741a6ca
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_J1_B_RL_1cm/result.json	d1d413c5d09b59f23c9c1c1c956daea1b9100592989fb5702b2af7c42dd3af0f
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16_J1_B_RL_2cm/result.json	d22d2421c252c3588989c5dda78326ee9db6ebb30781cdd17fdaf1b7664ea4ad
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16bp_J2_B_RL_1cm/result.json	2d1c0d7ae9330b1e76bc494d516f5aede1c1a71e717e0c386a59904c024d4ac6
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16bp_J2_B_RL_2cm/result.json	dea9384d973ab9916f91692459881514ab91147806ac6569ac33af94d65017b9
not_run_S9_level	S9/batch_P1_V16_20261026_032113/V16d_G1_B_RL_2cm_step/result.json	4c97f8a4f0080190d52f6fb84c5c61d72786abac630ee039f7ae6573d7705886
not_run_S9_level	S9/batch_P2B2_20s_20261026/P2B2_J1_top_M14s_20s/result.json	8196622eebb9beb0abb62d642fea0d9bc20a7c731600be04a24a03910186cb18
not_run_S9_level	S9/batch_P2B2_20s_20261026/P2B2_J2_top_M14s_20s/result.json	2e4948df74a89596e3648b411c9093d8a2700c4d3440a74ed47d6bc7696ae137
not_run_S9_level	S9/batch_P2_20261026_040423/P2-1_J1_top_M14s/result.json	4719111d398a67ac0cbd03c932decf2c0c10d591fce09d367632a830755dfdcb
not_run_S9_level	S9/batch_P2_20261026_040423/P2-1_J2_top_M14s/result.json	2d320d4574503ad509b797b2ad2e321eb444375cad562a2b47dcae67ec2d1236
not_run_S9_level	S9/batch_P2_20261026_040423/P2-1_S1_top_M14s/result.json	c4bbcdca7459fef0e2527bd518f3e2a709bd6e68110e02b0505f3d528e4e693f
not_run_S9_level	S9/batch_P2_20261026_040423/P2-2_J1_top_single2cm/result.json	2c57053fd5cda3efd69e1b23bb5378cf35f11262955034e0d3094bb53be2b7c7
not_run_S9_level	S9/batch_P2_20261026_040423/P2-2_S1_top_single2cm/result.json	2838cabbbebb8a72847c7db86096d33345416868bdf76a740616223681b6e7b2
not_run_S9_level	S9/batch_P2_20261026_040423/P2-3_G1_bottom_M14s/result.json	d187d603f53ee3e24e4ccff6d3896853a99fea73a64bc30b33daeac4dd109180
not_run_S9_level	S9/batch_P2_20261026_040423/P2-3_G1_middle_M14s/result.json	f53fad45b7bd40f68a9a893228df2d205b5a73a43ef18534d870f60b83c3498a
not_run_S9_level	S9/batch_P2prime_20261026_083209/P2prime_G1_top_M14s_dashpot8s/result.json	d41fa6052e941bc07cf871371b59eb8f6849af1db82931a2f8f7b10cc0b478d8
not_run_S9_level	S9/batch_P2prime_20261026_083209/P2prime_J1_top_M14s_dashpot8s/result.json	f74dca67fd5be79093dd7a5c0bf6ab86e58fa948bd32e8bb314473dd9c6ac4f8
not_run_S9_level	S9/batch_P2prime_20261026_083209/P2prime_J2_top_M14s_dashpot8s/result.json	d3dbe0d59a7fffce9c39d4ab38aea526d4daa4fd32fb853a59f30f77eb15124e
not_run_S9_level	S9/batch_P2prime_20261026_083209/P2prime_S1_top_M14s_dashpot8s/result.json	db35efc6f70d7af3218dfa129c4a3adf221482944f9842c86cb20207f66e0ed3
not_run_S9_level	S9/batch_P2prime_rep_20261026/P2prime_J1_top_M14s_dashpot8s_ramp2.95/result.json	4330e5a9e90ca426f01cf6fa5e5ea986159091d759497e10b62c8fd9ae3d3948
not_run_S9_level	S9/batch_P2prime_rep_20261026/P2prime_J1_top_M14s_dashpot8s_ramp3.05/result.json	f086e94ecb0a8fd339aed1953705e77f8a909ab640a55d503c7867c3b974ed4b
not_run_S9_level	S9/batch_P2prime_rep_20261026/P2prime_J1_top_M14s_dashpot8s_thr2/result.json	e04cbb3cd40c13118ea8303b79071f9c52a4b8dbd2d706de760a95302345c1f7
not_run_S9_level	S9/batch_P2prime_rep_20261026/P2prime_J1_top_M14s_dashpot8s_thr6/result.json	e6f7983d2ae9aba8666502bf94c9e82309fbb4dcd93b546cd8f89783714d3a0e
not_run_S9_level	S9/batch_P3-10_20261026_122444/flat__off/result.json	1ebbd54be5a696b092acf69f5fc5d9f171ccd57e17486591a8d9b1712a4f816f
not_run_S9_level	S9/batch_P3-10_20261026_122444/flat__on/result.json	7f55ffa9b2e50e4fe2cfb41a50f2595982d141078a92c7b117eef90cdaa29017
not_run_S9_level	S9/batch_P3-10_20261026_122444/rpB__off/result.json	258d2adc37c5de74917bcea862381ccdb3d6a17c6d98b4c75e1cda1b18096c1d
not_run_S9_level	S9/batch_P3-10_20261026_122444/rpB__on/result.json	6a58dedfe4dbb28a7ce6d2f8484576e77fd53160cae8f3d40c6c8d544045a928
not_run_S9_level	S9/batch_P3a_20261026_092653/P3a_G1_A/result.json	4b066f36b75af4285d5269f85b5ec46d27f01b6ce26665790cbf1b33c10a2abc
not_run_S9_level	S9/batch_P3a_20261026_092653/P3a_G1_B/result.json	7020035775771bcb29b4d6fc1dee395ca91fd9d44838484211afbf9518538e4d
not_run_S9_level	S9/batch_P3a_20261026_092653/P3a_J1_A/result.json	e1dcdc3eb886993d8d77657cd4ca232dbc4284da98e4a14fda29549560ef6403
not_run_S9_level	S9/batch_P3a_20261026_092653/P3a_J1_B/result.json	4400b57f9d97b4df602feef3497d2e2ccb83aab96261ffa95c76c8d48f4c1639
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_A_bottom_Fs4/result.json	6448a7bf970ea56f578d4ec56d802c466f0ac00eac232ab1b34903caf114f984
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_A_middle_Fs4/result.json	728e5c28095ab99000e77dfe0e4a42181c2d856107bc61d5b3a6ee91037ddcc5
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_A_top_Fs0/result.json	24cab6ede782a5bb190c505efc11bc8fb73acc840f526e8f6c0b848391e93a99
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_A_top_Fs4/result.json	a6555e09f8ac34bb2fd083b60c6d38090de2399c1163fe6bdfbaf336f7967568
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_A_top_Fs8/result.json	030d94de26c410834564f09f3a4ab60f93dc3ad7984e5db8184a7c913cf7a0c3
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_B_bottom_Fs4/result.json	41aa335ec2c82da474f4ca9e4e85e0bd4185773c3046f4375f0a8a8bb29847ba
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_B_middle_Fs4/result.json	9ba724163da072e74a9e7194325a9d13eeb5d04433db8704fa0a88a1d777cfe1
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_B_top_Fs0/result.json	d89a0cfd5e3456398b16e62e80e1721062d946d45ee5bcee7d8b5df51552ce99
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_B_top_Fs4/result.json	c9130f23f5f0f66259a85c12ccfa336bb04885396781f3dac60a360b9ed75580
soil_response_off	S9/batch_P3b_20261026_122444/P3b_G1_B_top_Fs8/result.json	5060bae71c9b8357eb9d6e2f8b7ea98bf2c502d8cabef0b0d04afa9af66165eb
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_A_bottom_Fs4/result.json	fd01183ca4ec47aa0b1c613d9e212c186268d4236ca1d9222291e6914cbe0921
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_A_middle_Fs4/result.json	94df8f1cbe5a065ff8bafc0ed2bf8ad72d58fdb03594e1ea67ed5f6c1d6c0dd7
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_A_top_Fs0/result.json	2ca0802a71d0171859e895d7f5bf96911c135204109c27e9aaa499a142eec115
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_A_top_Fs4/result.json	5b7023b6ad9c39632bba78a3806b587e200f9f8a8ce6584e49b9b3dbd41154d6
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_A_top_Fs8/result.json	39260566b9328540f766458c026b3cb44677a2dcb4f4239f96cdd6b3c2885fcf
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_B_bottom_Fs4/result.json	d16e15a5c02bf4ca05cac566f30bccf392ba7ef352317e929eebc74c9e69a5c4
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_B_middle_Fs4/result.json	9446b3a1fa0c0a83a14234c6697fc896830c5cdff0c31e8e06eceb3fc081c18d
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_B_top_Fs0/result.json	19efe8cb1984ab1ed7f2f739f69862fd19eedf783604fb08dd4f50e676d64404
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_B_top_Fs4/result.json	955dfddbeb9620e09e6339ac060231205bec3122c86fc220c42b3141facad190
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J1_B_top_Fs8/result.json	1e6ab4e8bd7c300cb31ed48fd3ccac616ad53a66b5390530ac321e8677e08fe0
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J2_A_top_Fs4/result.json	46698d91009e7c3183634a45c903aa10885874cdb1fcb6fbe95752ca7b0f1a5e
soil_response_off	S9/batch_P3b_20261026_122444/P3b_J2_B_top_Fs4/result.json	af5d2e2583bf08bc07685f1c57efbd9cac8054be3ab536b3f03dadc1b2ea06d6
soil_response_off	S9/batch_P3b_20261026_122444/P3b_S1_A_top_Fs4/result.json	c8fb392f2f17114d2b48f78113159199b3cd2bbcb468b5a87a8da80ebcb85d05
soil_response_off	S9/batch_P3b_20261026_122444/P3b_S1_B_top_Fs4/result.json	93307332388ae441b9f6df335ffe8235c71eaa46b22d38c505463c0854cd518d
soil_response_off	S9/batch_P3b_20261026_193021/P3b_G1_A_top_Fs0/result.json	24cab6ede782a5bb190c505efc11bc8fb73acc840f526e8f6c0b848391e93a99
soil_response_off	S9/batch_P3b_20261026_201553/P3b_G1_A_top_Fs8/result.json	030d94de26c410834564f09f3a4ab60f93dc3ad7984e5db8184a7c913cf7a0c3
not_run_S9_level	S9/batch_V5-OPENLOOP-FB_20261108_183849/P3a_J1_B_V0_FB/result.json	7800d73f8d512774c14f1661255b446b9be83b7bb797e03436532f8fd1b5ce5c
not_run_S9_level	S9/batch_V5-OPENLOOP-FB_20261108_183849/P3a_J1_B_VB_FB/result.json	dccedf30d4fdcff7c5870c22d9e4a4bfef5676f6c3e787da1e42158faa3eaeb1
not_run_S9_level	S9/batch_V5-OPENLOOP-RFU_20261109_0100/P3a_J1_B_V0_R1490k/result.json	7a2c092cc775b63852122d1efae8e7e563309fd033e1284819dff197f039a728
not_run_S9_level	S9/batch_V5-OPENLOOP-RFU_20261109_0100/P3a_J1_B_V0_rep/result.json	7e2b42d9160837d3b8322d5acfb642a8f95fb864de1b6eb8d1da9ae365ab0de1
not_run_S9_level	S9/batch_V5-OPENLOOP-R_20261108_231840/P3a_J1_B_V0_R300k/result.json	6f604df6e2c0aa55feb67771e5684df595a6b8df905e9f6d3140b47654cb68b5
not_run_S9_level	S9/batch_V5-OPENLOOP-R_20261108_231840/P3a_J1_B_V0_R600k/result.json	b2b47bf6e607415803d3d290571b99013b44c9e807340886d0d36c7e66d477c7
not_run_S9_level	S9/batch_V5-OPENLOOP-R_20261108_231840/P3a_J1_B_V0_R888k/result.json	e110325c6e5e10e52ad3965c84e5d600a71884ff985e32591b5b38bf4debc49b
not_run_S9_level	S9/batch_V5-OPENLOOP-V0_20261108_123517/P3a_G1_B_V0/result.json	068e37f77b28af0243caf4a3338cb9dfc26283f207890208ac659df8500ea825
not_run_S9_level	S9/batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0/result.json	349b6f072197d59aafdcec9910986170b90b1f0162378862c21f514f35528ec1
not_run_S9_level	S9/batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop/result.json	5330e5e38ebd9aaf2f21b788d01680e5367b5358d07f6f2dfb8ec6190143a19d
not_run_S9_level	S9/batch_V5-OPENLOOP-VB_20261108_112044/P3a_G1_B_VB/result.json	bfa510270e13983daa13b57f8ec5dadfa575bcc6cc63ded438daabe1d4a021b1
not_run_S9_level	S9/batch_V5-OPENLOOP-VB_20261108_112044/P3a_J1_B_VB/result.json	f81acbcdeb5b36c385e19ff296a3db3bc8c2f83933784088aab8d2432eb3ccd6
not_run_S9_level	S9/batch_g8c3_20261105/G8C3_top_edge_RL_g230_C4G2/result.json	01d73389ebfc7c65d51c802d6627aef3263405386660e4aed87663ec9c1bc878
not_run_S9_level	S9/batch_g8c3_20261105/G8C3_top_rpB_RL_g230_C4G2/result.json	80011f87672aef46727d3c9586d305fb2d353df6abc847a4f0afee734e3e592d
not_run_S9_level	S9/batch_g8c3_20261105/G8C3_top_rpB_RL_g230_off/result.json	bbc0d971118bd294663ca46e7797fe75287f2a09e7a199be212b51bd2fb4e94a
not_run_S9_level	S9/batch_g8c3_20261105/G8CL2b_top_rpB_RL_g230_Fs4_C4G2/result.json	aac8bcb1e26eca37c3e7ae5e594f4b88d6a46410c714343304cee81d8b69b6bb
not_run_S9_level	S9/batch_g8c3_20261105/G8CL2b_top_rpB_RL_g230_Fs4_off/result.json	1e99c29b1a729e1c395064ae3ddabb4ae0f54848dba46af436270b2e82b32039
soil_response_off	S9/cost_M1_P4/cost_M1_P4_1/result.json	6347659ed2e3f521158af034161db7b8779587da8b5e7f3ff5725f6310d0d840
soil_response_off	S9/cost_M3_E4/cost_M3_E4_1/result.json	2356ff3c1ed3f7e1bd14310776d467407815dda938910e5174acab9e2527a39c
soil_response_off	S9/cost_M4_J1_P4/cost_M4_J1_P4_1/result.json	f1c6b7bc64b78b799b60f4b911db23db720ca4619143606926511e4314be12e3
soil_response_off	S9/cost_solo_20261026_230636/solo_G1_B_top_Fs4_end40/result.json	8a813f08ced39d97b70b341d0ea44ca5c0ccb6ebbc964c7ebcff7cbe43d08a19
soil_response_off	S9/cost_solo_20261026_230636/solo_J1_B_top_Fs4_end40/result.json	2d32d2b096e66e87c5dd059250d700a2519e1022172042829b2083c75a069c33
soil_response_off	S9/cost_solo_20261026_230636/solo_J2_B_top_Fs4_end45/result.json	03c11fb5141c2665450d02ddb6b82982f79a1213b35e885acfc73949447fd2d6
soil_response_off	S9/cost_solo_20261026_230636/solo_S1_B_top_Fs4_end50/result.json	b73b370b882772718a446fffd4d4d3808ecc359e3413d17a697999e501926165
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_2cm_c2cm_poly3450.5_lift0_20261026_021012/result.json	bc6915999b22e377bc320637e37ac071a23121f06a802355b0e4dc33e92ebad8
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_2cm_c4cm_poly3453_lift0_20261026_023156/result.json	55d16ea634ff16a482daa764c41de73a94147e21c58f45436e820499eb3af00f
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_2cm_poly3450.5_lift0_20261026_021011/result.json	9b6d505d8f6e227251441e5962f5bd6f4c993a0a244b01d72b34fcb3e36a18a9
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_2cm_poly3453_lift0_20261026_023833/result.json	2f22ae710ce9195d4bb8cd621730fd24cd2760beb07ec89c98fb9152fe4e79f0
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_4cm_poly3450.5_lift0_20261026_020644/result.json	d28ec4031485bb9965a83210de79eb7a8e2c5554f11eb3a4b287ea5d9ec5ed67
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_4cm_poly3450.5_lift0_20261026_020650/result.json	ebe8bbde9db8aecad6a55ecdf6879c2dfbde5c4a9a1473ad5a0eb8649b10ceb8
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_4cm_poly3453_lift0_20261026_020251/result.json	069fed0f62847b1ee7f90d15d530237e8bd6e3ee6833534047d4a71e68ef857c
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_lift0_20261026_004539/result.json	199b6b7f9cde2993739b0c684af5bb781e922785641888cd9456da26318d1aea
not_run_S9_level	S9/machine_G1_dwg_rear250_bprime_lift0_20261026_005521/result.json	1cf49dd066c71e359b856ece1e3d98c4261c9b878cd3ffd847efb550bf1ba93d
not_run_S9_level	S9/settle_ramp_G1_2cm_poly3453_20261026_013534/result.json	20751926774772173f6efdfa5b525f960ae042c9131fd2ea0775ead8790534f4
not_run_S9_level	S9/settle_ramp_G1_4cm_poly3453_20261026_011854/result.json	d92fba79fb2fe5ca45b345caf7bae2dab8a58781b91dbd30965852a011b6c9e8
not_run_S9_level	S9/settle_ramp_G1_4cm_poly3453_z3mm_20261026_013652/result.json	72f4eb12b9e5981647e354c2e51cefb3b9914cfd48d7c2df4edd236dbda2b900
not_run_S9_level	S9/single_G1_dwg_rear250_RL_bprime_F0_20261026_015801/result.json	5d7ecffded6c45c0783c87ca6762493bceeef0f3e8673f633f44da8fc269bb6d
not_run_S9_level	S9/single_G1_dwg_rear250_RL_bprime_F0_20261026_015905/result.json	7385ed4db3a842fec1ca473011625a0edbcead194cf729e9e984eefa4929065b
not_run_S9_level	S9/single_G1_dwg_rear250_RL_bprime_F4450_20261026_004137/result.json	51f31a0a378a02fd72e8897700588c9e303897e422ceaff4ce1e9515fac3700b
not_run_S9_level	S9/single_G1_dwg_rear250_RL_bprime_F4450_20261026_004237/result.json	12641e2370b66039768e7ba5729dccf8b471fb6628094ed1103d0e7d1b90f980
not_run_S9_level	S9/single_G1_dwg_rear250_RL_bprime_F4450_20261026_015836/result.json	880da63ff7f32d5bd325df992023b97d18316ae230aa22493d323ff0b5a49684
not_run_S9_level	S9/single_G1_dwg_rear250_RL_native_F4450_20261026_005152/result.json	0babbdb53c223da68b3077dcac3e4311078449c27a6105487571961343f33fff
not_run_S9_level	S9/single_G1_dwg_rear250_RL_native_F4450_20261026_012010/result.json	d70227968ecde9e4b6550e6435cf4f4c21fd9b00576961ca1f063a214c8d3245
not_run_S9_level	S9/single_G1_dwg_rear250_RL_native_F4450_20261026_012140/result.json	ea742b26e84774db699be7efceeb3aca5e83782760cc51eac7330abe816f437c
not_run_S9_level	S9/single_G1_dwg_rear250_RL_native_F4450_20261026_012228/result.json	64d4e5c6bae07db37c5aa8829d4b6a84e0cbcf97857a584b0c0d134258440e1b
not_run_S9_level	S9/v4_20261027_010707/c36_smoke/ML88_ep0/result.json	164a82467853cc4513f5d2308f0a6a4e7150b7ad49ffc2aaf78902948ba3723c
not_run_S9_level	S9/v4_20261027_010707/m3_column_nominal/rpB__on/result.json	f93f91d46e25ab000bd054ac32e898da18decce6dbbe444d5f81de5b57bae722
not_run_S9_level	S9/v4_20261027_010707/m3_plant_meta/rpB__on/result.json	ce85d7878f033594e6316dcf8114a7e537558337d111106aa9df4b1e2cb37579
not_run_S9_level	S9_merge/m3_20261026/flat__off/result.json	4583f6064924894c0658984c80eca161d6b7fe8b43c6b0c16c5f7944e82bcad6
not_run_S9_level	S9_merge/m3_20261026/flat__on/result.json	16eb3b88eca46bbff34ecb1e321bdb3363b461ddd278a21800ed28e34f83a9e4
not_run_S9_level	S9_merge/m3_20261026/re1bf_l1__off/result.json	da93ce33b126365a4e18a2e4eb76194c1e8f2506f1071e37df61c64a85e99cba
not_run_S9_level	S9_merge/m3_20261026/re1bf_l1__on/result.json	6cdef1db1492f76844dbfe228cbe5182b6726e557a8e965f28420832fbe1a447
not_run_S9_level	S9_merge/m3_20261026/roll55__off/result.json	55e98576b75f2c8b36dc1ad21fac748622798876644d5cddd82faee83c24b995
not_run_S9_level	S9_merge/m3_20261026/roll55__on/result.json	8b8e2d3ab15c57ff5e7a87763f957b25b1a6d63946a6144fb2fc76628660903c
not_run_S9_level	S9_merge/m3_20261026/rpB__off/result.json	2690a02f34ffa2d14c01badee4d04475b338bcf380c119ca635a17d51d420d7e
not_run_S9_level	S9_merge/m3_20261026/rpB__on/result.json	a6e044bab42312be54ebc3fcc41404d6573f9760f455758ef1fc80e77b506fd3
not_run_S9_level	S9_merge/m3_20261026/s8_re1bf__off/result.json	9dae15c825f94863a102f4c00cb51351374633de29e82aa0bfede87c8b5aa8e2
not_run_S9_level	S9_merge/m3_20261026/s8_re1bf__on/result.json	d5ca8c1fed1a8a8cf8fd3437ec2f5165af68d2aeaef0b170c54cea2f7dfe19cd
not_run_S9_level	S9_merge/soil_restore_20261026/bases_on/ML10/result.json	c5c9072823e547f04cba773c59f92beb504a433fc9bb0d174bef774a2cec9156
not_run_S9_level	S9_merge/soil_restore_20261026/bases_on/ML17/result.json	720ca8265cfab4b1dd982488aed37aa1aa3cc0f32da47e4b36a679f4d01f2b84
not_run_S9_level	S9_merge/soil_restore_20261026/bases_on/ML21/result.json	6af98b19aa0090bd926fac2f25cc625c571ace7d31de703fb4f6c2b8a7466475
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_native/ML10_ep1/result.json	0c9901d2678e5f69d530a575716e1379aba2f5deb8d431420a412059f7b28378
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_native/ML10_ep7/result.json	c739385dc3022f3ab6786ed5d1b2e04699f39270e079b0a9be3fff954fdd7c5b
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_native/ML17_ep1/result.json	d010e2375bd3b61c3c8bbc2fcabc9439c46b0f604c2ed020f964731cbabbc558
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_native/ML17_ep2/result.json	7470dfd2180014f145797f8f8a9ed7eb327e1e490576fe8d43a2a6098bd4ba26
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_native/ML21_ep3/result.json	f456d29011aaa7d87770dda311696803789cb02619996391035e4f89a735f9f5
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_native/ML21_ep6/result.json	31329664dc7547ef2ed0135f5a726e3bdcc65b8edb3cbe0ad52de0d2e0242f79
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_restored/ML10_ep1/result.json	069dce9c440cbc5e17fa93d08392d56b4b47c29b1a7f8e523c527c2224a2c524
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_restored/ML10_ep7/result.json	bc553becf2231081baa19d279039ccafbb1a0d93d3b62927dd93d4cf3b6a6ab2
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_restored/ML17_ep1/result.json	71bb01b7881db4414957b789cd0d4d480fd6ef3ddbbd275a3ba4da2654f3f232
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_restored/ML17_ep2/result.json	9c741f05285f1bf3835b41df9bc455ef2f3b27b98ea6c61c3defdc4f18de2024
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_restored/ML21_ep3/result.json	463deb0ba20456c4661b362b9d2ac1f72d0b6911e11bd874d1ffaadc2c526c2c
not_run_S9_level	S9_merge/soil_restore_20261026/episodes_restored/ML21_ep6/result.json	4785be6a43f94da384b31bd9272e903a37b6574695bee8a0750f577eb3980eb7
not_run_S9_level	S9_merge/soil_restore_20261026/old_bases_R3/ML10/result.json	b6bc2e2aa7f870db520181c2a8d7b4852fb2e12f06762049a7164358cac498f4
not_run_S9_level	S9_merge/soil_restore_20261026/old_bases_R3/ML17/result.json	22de466d85de912d7df97953169f4e9ed11e0a100596b309e0201d8f0660cc72
not_run_S9_level	S9_merge/soil_restore_20261026/old_bases_R3/ML21/result.json	e5130fa8ec9a8566e834f43285dec9af7a9d407162812fab46a26aed79b0c08d
```

- 전체 모집단 U 300행 정규 목록 sha256: `41e01c20e45400151120e3667f3805c0fad98a279ba50fb02c054d162a1ccd79`
