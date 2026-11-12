# B1 크리프 근거 — 사전 등록 규칙 초안 v2 (`V5-B1-CREEP`, 후보판 이어받음)

- 작성: control-expert, 2026-11-11. 작성 기준 master `7a469f7`(작성 시점 HEAD. 실행 HEAD가 아니다).
- **상태: 초안. 봉인하지 않았다.** `.sha256`이 없다. 이 파일로는 실행·판정하지 않는다.
- **시점: 결과 전.** B1 Chrono 6행·하네스 28실행은 0행 실행됐다. 이 초안은 B1 결과를 하나도 보지 않고 썼다.
- **이어받는 판**: 봉인 후보판 `b1_creep_basis_rules.md`(마지막 커밋 `ba84f53`, sha256 `7c782632aa9796a5109a5bce9035beff844bb4f290b7cd60c4f25ae5eb8c1524`, blob `9b600c5f`). 그 판은 봉인되지 않았다. 이 초안은 그 판을 대신할 다음 후보다.
  - 이 초안에서 "후보판 X절 그대로"라고 적은 곳은 위 sha의 그 절 문장을 그대로 쓴다.
  - 봉인할 때는 두 파일을 합친 **한 파일**을 원판으로 만든다(사용자 결정 U-1 권고). 후보판 파일은 고치지 않는다.
- **이미 봉인된 B1 관련 규칙**(이 초안이 전제로 이어받음, 바꾸지 않음)
  - 격자 시험 계획 `b1_gridconv_plan.md`(`0e909bf1…9b24`, 봉인 2026-11-10 16:35:32) + rev1 `b1_gridconv_plan_rev1.md`(`3f354eb7…da9e`, 16:50:36)
  - 그 판정 `b1_gridconv_judgement.md`(`a483ac48…e56b`): `PASS`. 후보판 봉인 전제(격자 시험 `PASS`)는 이미 충족됐다.
- 봉인 시점(후보판 그대로): P5r4+K1 판정·채택 결정으로 2절 파라미터가 정해진 뒤.

## 0. 이 초안을 쓰려고 본 것과 보지 않은 것

### 0.1 본 것

- 후보판 전체, 초안 `b1_creep_basis_plan_draft.md` 첫머리, 격자 시험 계획·rev1·판정서 sha, 격자 시험 실행 전 감사 `b1_gridconv_prerun_audit.md` 발견 1~11
- `decision_log.md` 4절 끝(11-09~11-11: K1 채택, D8x 미달, K-2 판정 불가·채택 안 함, v5 제어기 확정, 다음 순서 P5r4+K1 → B1 → 436.8)
- 로드맵 13·14항, 인계 문서 `00_docs/handoff/session_handoff.md`
- LOC 앵커 검토 `06_analysis/02_control/k2/judgement/loc_anchor_review.md` 0~3.1절, 그림자 진단 `06_analysis/02_control/k2/loc_shadow/hsh_report.md` 0·1·4절(둘 다 B1·P5r4 결과가 아니다)
- P5r4+K1 **규칙** rev3 `verif_matrix/las_p5r4_k1_rules_rev3.md` 첫머리와 RV3-0.4 항목 대조표(규칙 형식의 교훈만, 결과 아님)
- 코드(읽기만): `03_src/outrigger_sim/control/c2.py` 200~225·2166~2215·8955~9070행(E3c10·R4c30·K1 순서 관문), `04_scripts/02_chrono/s9_batch.py` 391~437행(`V5_*_CONTROLLER`, `v5_vb_argv`, `v5_vb_rows`), `04_scripts/02_chrono/run_S9.py` 445~500행(`--start-limit`), `04_scripts/03_control/k2/loc_shadow/loc_anchor_shadow.py` 40~80행
- 명세 `s6_control_spec.md`에서 "426.9.B1" 제목 줄(이름 겹침 확인용, 6.4)

### 0.2 보지 않은 것 (금지)

- LAS-b P5r4+K1 결과: `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/`(jsonl·judge json·prelaunch 포함 폴더 전체), `06_analysis/02_control/verif_matrix/p5k_judge/`, `07_results/S9/batch_V5-LAS-P5R4-K1*`
- 그래서 `P5R4_OUTCOME`과 그에 딸린 파라미터는 이 초안에서도 **미정**이다.

## 1. 이어받기와 새로운 것

| # | 구분 | 내용 | 절 |
|---|---|---|---|
| Δ-1 | 바뀜 | 제어기: K-2(`_TCL`)는 판정 불가·채택 안 함(11-11), **v5 = `final_C4G2_LAS_K1` 확정**. 후보판이 쓰인 11-10에는 K-2 결과에 따라 태그가 바뀔 수 있었으나 그 갈래가 없어졌다. 남은 갈래는 P5r4 채택 여부뿐 | 2 |
| Δ-2 | 새 | 태그 접미사 함정 규칙: 기대 태그는 문자열 완전 일치, 부분 문자열·접두 판별 금지, `v5_vb_rows()`(옛 `final_C4G2_P3` 고정)로 행을 만들지 않음 | 2.2, 3.3 |
| Δ-3 | 새 | 옵션 × 단계 겹침 표(K-2 재발 방지 1항) | 3.3 |
| Δ-4 | 새 | G-S 건조 실행(K-2 재발 방지 2항) | 3.4 |
| Δ-5 | 바뀜 | P-A의 $m_L$ 정의: E3c10(`INFO_LOC_CLEARANCE_MARGIN`)만이 아니라 **실행 틈 목표를 올린 두 사건**(E3c10, R4c30 `INFO_LOC_FLAT_SOIL_MARGIN`)의 실효 목표로 읽는다 | 5.2 |
| Δ-6 | 새 | H-M0($m$ = 0)의 구현 꼴을 못 박음: `margin_m = 0`, `enable` 유지(끄면 R4c30이 대신 켜질 수 있음) | 3.3, 5.2 |
| Δ-7 | 새 | M-12 LOC 앵커 기록(단일 표본 자세 결함, 11-11 검토). 등급에 쓰지 않음 | 5.3 |
| Δ-8 | 새 | 문턱 비교 허용 1×10⁻⁹ m(값 대조 허용과 분리)과 비교 꼴 전수 표(P5r4 rev3 RV3-1 교훈) | 4 |
| Δ-9 | 새 | 시각 비교는 정수 주기 $n = \mathrm{round}(t/0.1)$(RV3-6 교훈) | 4.2 |
| Δ-10 | 새 | 러너 로그 `errors N`·`errors_left`, 자리표시 점검, prelaunch는 추적 밖에서 채움(RV3-2·RV3-3, K-2 재발 방지 3·4항) | 7, 실행 전 기록 초안 |
| Δ-11 | 제안 | D-a를 원시·보정 중 보수 쪽으로 등급(격자 시험 원시 차 RL +2.74 mm가 문턱 3 mm와 같은 크기). 사용자 결정 U-3 | 5.1 |
| Δ-12 | 새 | terramechanics 재검토 항목(11-10 검토는 격자 시험 결과 전이었다) | 10 |
| Δ-13 | 바뀜 | 순서·비용: D8x Chrono 19행은 실행하지 않았다(B-G1 미달). P코어 순서를 고침 | 11, 12 |
| Δ-14 | 새 | 이름 겹침 주의(명세 426.9.B1 = 연구 B ×1.1, 3단계 H-7 기전 B1, 하네스 키 `K1`) | 6.4 |
| — | 이어받음 | 목적·예측식, Chrono 6행·하네스 28실행, 행 유효성 V-1~V-4, 묶음 상태, 등급 D-a~D-h의 양·문턱 값, 3.4 격자 영향 표, 지표 M-1~M-11, 5.1 격자 기록 요구, 예측자 후보·상수, SGS 하한 처리, 예측 P-1~P-9, 두 경로 재집계, 세 시점 감사 | 후보판 0~13절 |

## 2. 파라미터

### 2.1 표 (후보판 1절을 대신함)

| 이름 | 정하는 규칙 | 값 |
|---|---|---|
| `P5R4_OUTCOME` | P5r4+K1 판정서와 사용자 채택 결정 | `adopted` / `not_adopted` / **(미정)** |
| `CTRL_TAG_VB` | `not_adopted` → `final_C4G2_P3_LAS_K1`. `adopted` → 채택 전환이 정한 VB 태그(전환 뒤 `v5_options.is_extend_start_tag`가 참인 태그) | **(미정)**. K-2 갈래는 없어졌다(Δ-1) |
| `CTRL_TAG_V0` | 같은 규칙, `not_adopted` → `final_C4G2_LAS_K1` | **(미정)** |
| `CTRL_PRESET_NOTE` | 프리셋이 바꾼 기본값 목록. `not_adopted`면 "K1 채택 프리셋 그대로(LAS-b + K1 순서 관문 켬, `_TCL` 끔)" | **(미정)** |
| `HEAD_M` | 실행 커밋. 파라미터를 반영한 원판 병합 뒤, 깨끗한 checkout 또는 그 커밋 고정 worktree | **(미정)** |
| `P7_REF` | 후보판 1절 그대로 | **(미정)** |
| `HULL_DLL_SHA` | `hull_hook.VALIDATED_DLL_SHA256`, 현행 `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(격자 시험 prelaunch 기록값) | 봉인 때 다시 확인 |
| `START_LIMIT` | `record_only`(terramechanics T-6 권고, 후보판 R-2). cad-expert가 확인 | **(미정, 권고 `record_only`)** |
| `POOL_ROWS` | 행별 P/E. 사용자 결정 Q4(스케줄러가 정함) 그대로. 프로젝트 규칙상 P 우선 | **(미정)** |

- 후보판 1절의 "`adopted`이고 E3c10·LOC 취소·SGS·DSb75 가운데 하나의 기본값을 바꾸면 그대로 봉인하지 않는다"를 그대로 둔다. **R4c30과 K1 순서 관문의 기본값을 바꾸는 전환도 같은 취급**으로 넓힌다($m_L$이 두 사건을 읽기 때문, Δ-5).
- 봉인판에는 `(미정)`·`{이름}` 꼴이 남으면 안 된다(실행 전 감사 S, `placeholder_scan.py`).

### 2.2 태그 규칙 (새)

- `--expect-controller`와 하네스 태그는 2.1 값과 **문자열 완전 일치**로 확인한다. `_K1`·`_LAS`로 끝나는지, 접두가 같은지로 판별하지 않는다.
  - `final_C4G2_K1`(LAS-b 끔 + K1), `final_C4G2_LAS`(K1 전환 전), `final_C4G2_P3`(③ 단독)은 모두 다른 제어기다.
  - ③(VB) 여부를 코드가 판별해야 하면 `v5_options.is_extend_start_tag`를 쓴다. 집합 `EXTEND_START_TAGS`는 쓰지 않는다(프로젝트 CLAUDE.md).
- `s9_batch.v5_vb_rows()`는 `--expect-controller`를 `V5_P3_CONTROLLER` = `final_C4G2_P3`로 바꾼다(`s9_batch.py:391, 423-437`). **B1 행은 이 함수로 만들지 않는다.** `v5_vb_argv()`로 옵션만 받고 `--expect-controller {CTRL_TAG_VB}`를 따로 붙인다.

## 3. 대상 행·묶음

### 3.1 Chrono 6행 (후보판 2.1 그대로)

C1~C6(J2 균일, 패드 B, $F_s$ 4 kN, VB, 격자 `--grid 0.01 --crawler-grid 0.04`, `--settle-dashpot zrp`, `--threads 4`, C1~C5 160 s, C6 ×1.1 180 s, 압력 `normal`, IMU `ideal`, 시드 P3b 기본). 표는 후보판 2.1절이다. 바뀐 것은 `--expect-controller` 값을 만드는 방법(2.2)과 `--start-limit` 값(2.1 `START_LIMIT`)뿐이다.

### 3.2 하네스 (후보판 2.2 그대로 + 그림자)

- H-P 20, H-W 4, H-M0 4 = 28실행. 태그 `{CTRL_TAG_VB}`/`{CTRL_TAG_V0}`.
- **새(선택, U-7)**: 28실행 모두 `OUTRIGGER_LOC_SHADOW=1`(기록 전용 그림자)로 돌리고, H-P VB e0 4실행은 그림자 끈 짝을 더 돌려 명령 해시가 같은지 본다(H-SH 456/456 같음 선례). 해시가 하나라도 다르면 그림자 기록은 버리고 그림자 끈 28실행을 다시 돌려 그것을 쓴다.
- H-W는 하네스 질량 배율이 있어야 한다. `04_scripts/04_hydraulic/coupled/run_v5.py`에서 `mass_scale` 인자를 찾지 못했다(grep, 2026-11-11). 후보판 R-4는 열려 있다.

### 3.3 옵션 × 단계 겹침 표 (새, K-2 재발 방지 1항)

행을 만드는 옵션이 같은 단계를 두 번 바꾸거나 서로 막는지 미리 적는다. cad-expert·python-expert가 실제 코드로 칸을 확인하고, 실행 전 감사가 대조한다.

| 옵션 | 바꾸는 단계·설정 | 겹칠 수 있는 옵션 | 겹치면 생기는 일 | 정한 처리 |
|---|---|---|---|---|
| `v5_vb_argv()` | 유량 포화, 밸브 τ, 로드측 해제, 잠금 겹침·닫힘 지연, 잠금 창 플랜트 추종, ③ 추적 | `v5_vb_rows()` | 기대 태그가 `final_C4G2_P3`로 덮임 → I-3 실패 | 2.2: `v5_vb_rows()` 금지 |
| `--expect-controller` | 러너 태그 검사 | 래퍼·프리셋 | 프리셋과 래퍼가 같은 규칙을 두 번 켬 | 래퍼 없이 프리셋만. `controller_meta`로 확인(I-3) |
| `--start-limit record_only` | `target.acceptance` OFF만(`run_S9.py:464-500`). LEVEL 경로·S-3·P-S8-28·REANCHOR는 프리셋 그대로 | 시작 조건 판정(V-3) | 시작 거부가 구조적으로 생기지 않음 → V-3 `MISSING_START`는 0이 정상 | V-3는 그대로 두고, $R_c$ > 1이면 기록(SL-2 FLAG) |
| `--mass-scale 1.1`(C6) | 플랜트 질량·관성 ×1.1, 무게중심 유지 | 제어기 질량(D1″ 명목) | 제어기에 배율이 새면 감도 실행이 아님(메모리 sensitivity-override) | 제어기는 YAML 명목. C6 `result.json`에서 제어기 질량 = 명목 확인(I-11) |
| H-M0 $m$ = 0 | E3c10 `margin_m` = 0 | R4c30(`flat_soil_margin_m` 0.03) | `enable=False`로 끄면 E3c10이 안 켜진 것으로 보여 R4c30 조건(정착 기울기 ≤ 1°)이 맞을 때 +30 mm가 대신 켜질 수 있다(`c2.py:8988-9013`) | `enable` 유지 + `margin_m = 0`. 그러면 E3c10이 +0으로 실행 목표를 정해 R4c30이 막힌다. 사건 `INFO_LOC_CLEARANCE_MARGIN:50` 기록 확인 |
| `OUTRIGGER_LOC_SHADOW=1`(하네스만) | 그림자 훅 설치, 기록 추가 | 명령 경로 | 명령이 바뀌면 판정 실행이 아님 | 3.2 해시 짝 |
| `OUTRIGGER_HULL_HOOK` | SCM 볼록 껍질 fast | 상속 env | 계획 밖 값 상속 | 실행 셸에서 지우고 미설정(기본 fast)으로. I-7 |
| 격자 기록 R-G1~R-G3 | 기록만(`GetNodeInfo` 읽기) | 패드 힘 | 기록이 힘을 바꾸면 판정 실행이 아님 | 켬·끔 짧은 짝 `step_series.npz` 비트 동일(후보판 5.1) |
| `OMP_WAIT_POLICY=PASSIVE`, `--threads 4` | 실행 정체성 | 풀 배치 | 스레드 수가 다르면 비트가 다르다 | I-4·I-5 |

### 3.4 G-S 건조 실행 (새, K-2 재발 방지 2항)

- 목적: 본 실행 전에 argv 꼴마다 러너가 시작·정체성 검사·기록 필드를 통과하는지 본다. 판정 값을 보지 않는다.
- 대상: argv 꼴 2개(C1 꼴 ×1.0, C6 꼴 ×1.1). `--duration 10`, 같은 `HEAD_M`, 같은 env·풀. 하네스는 H-P VB e0 1실행, H-M0 1실행.
- 출력으로 보는 것: rc, `expect_controller.ok`, 태그 문자열, `hull_hook` 값, `num_threads_chrono`, 격자 기록·M-4h·M-12 입력 필드의 **키 이름 존재 여부**, 러너 로그 `errors N`. 힘·행정·침하·시각 값은 출력하지 않는다.
- 공개: 판정서 1절에 시각·명령·출력 범위를 적는다(P5r4 rev3 RV3-0.3 꼴). 건조 실행 폴더는 본 배치 폴더와 다른 이름으로 두고, 끝나면 키 목록만 남긴다.
- 건조 실행이 실패하면 원인을 고치고(코드 수정이면 `HEAD_M`이 바뀐다) 다시 건조 실행한다. 본 실행 전에 봉인 규칙이 바뀌면 개정판이다.

## 4. 기준·문턱과 근거

### 4.1 문턱 표와 비교 꼴 (값은 후보판 3.3 그대로, 비교 꼴은 새)

허용 $\varepsilon_{th}$ = 1×10⁻⁹ m(시각은 4.2). 문턱과 차가 $\varepsilon_{th}$ 안이면 "같다"로 보고 아래 포함 쪽으로 분류한다. 이 허용은 두 경로 **값 대조 허용**(8절, 1×10⁻⁹ m)과 다른 문장이다. 두 경로는 같은 꼴로 비교한다.

| # | 등급 | 문턱 | 통과(앞) 쪽 꼴 | 근거(출처 유형) |
|---|---|---|---|---|
| T-1 | D-a `ZA-1` | 3 mm | $Z_{ch} - Z_{hn} - 0.003 \le \varepsilon_{th}$ | 0.2 저장 Chrono − 하네스 −0.25~−5.4 mm(후보판 0.2, 저장 결과) |
| T-2 | D-b `OS-MAX` | 5 mm | $O - 0.005 > \varepsilon_{th}$이면 `OS-MAX` | 0.2 $\delta^{os}$ 2.1~24.2 mm(저장 결과), 운용 판단 |
| T-3 | D-c `H-OK` 띠 | ±3 mm | $\lvert\Delta^{corr}_r\rvert - 0.003 \le \varepsilon_{th}$이면 "0". "+" = $\Delta^{corr}_r - 0.003 > \varepsilon_{th}$, "−" = $-\Delta^{corr}_r - 0.003 > \varepsilon_{th}$ | T-1과 같음. 대체 범위 분류(후보판 3.3)도 이 꼴로 구간 끝을 비교 |
| T-4 | D-d `PRED-FAIL` | 10 mm | $\min_q E_q - 0.010 > \varepsilon_{th}$이면 `PRED-FAIL`. 같음 판단 $\lvert E_q - E_{q'}\rvert \le \varepsilon_{th}$ → 단순한 쪽 | 0.2 예측 범위(저장 결과), 가정 |
| T-5 | D-e `NEED-RECHECK` | 20 mm | 세 행 모두 $g_r - 0.020 \ge -\varepsilon_{th}$ 그리고 SGS 0 | 0.2 하네스 P0 여유(저장 결과), 가정 |
| T-6 | D-g `W-OK` | $E_{q^\ast}$ + 5 mm | $\lvert e(\mathrm{C6})\rvert - E_{q^\ast} - 0.005 \le \varepsilon_{th}$ | 가정 |
| T-7 | M-11 기록 없음 | 간격 1.0 s, $N_h$ < 3 | 간격은 정수 주기 $n_\tau - n_{rec} > 10$이면 "기록 없음". $N_h$는 정수 비교 | 가정(후보판 13) |
| T-8 | 안전 기록: 다리 부상 | 접촉력 0이 0.1 s 이상 | 1 ms 계열에서 연속 표본 수 ≥ 100 | 가정 |
| T-9 | 안전 기록: 크롤러 재착지 | 이탈 뒤 0.01 W 이상 | $F_{cr} - 0.01W \ge -\varepsilon_F$, $\varepsilon_F$ = 1×10⁻⁶ N | 명세 P3-7 꼴 |
| T-10 | 5.1 격자 기록 비용 | 5 % | 기록 켬/끔 벽시계 비 − 1.05 ≤ 0 | 가정 |
| T-11 | 4.3 재실행 V-1 끝 시각 | `--duration` − 0.1 s | 정수 주기 $n_{end} \ge n_{dur} - 1$ | 후보판 3.1 |
| T-12 | P-2(예측, 기록) | 1.0 s 창 < 0.1 mm/s | `p3b.creep_stop`의 저장값을 그대로 읽음(다시 계산하지 않음) | 현행 규칙 |

- 이 표에 없는 문턱이 도구에 있으면 실행 전 감사 R에서 차단한다(메모리 threshold-tolerance-two-path).
- mm 표시는 보고용이다. 도구는 m로 비교한다.

### 4.2 시각과 표본

- 10 Hz 시각($t_L$, $t_{L1}$, $t_R$, $t_{\max}$, $t_{end}$, 사건 시각)은 정수 주기 $n = \mathrm{round}(t/0.1)$로 저장·비교한다. "같은 표본"은 $n$이 같다는 뜻이다.
- 1 ms 계열 조회는 후보판 M-4 그대로 `searchsorted(t, τ − 1e-9)`이고, $\tau = n \cdot 0.1$ s다.
- $t_{\max}$ = 모든 다리 판독 행정 최대가 처음 나온 $n$(같은 최대가 여러 $n$이면 가장 작은 $n$, 최대 비교는 $\varepsilon_{th}$).

## 5. 판정 등급

### 5.1 등급 D-a~D-h (후보판 3.3 그대로, 아래만 다름)

- 행 집합 $\mathcal R$, 예산 다리 $b^\ast$, 등급 이름과 효과는 후보판 그대로다.
- **D-a(제안, U-3)**: 원시 $Z_{ch}$ 등급과 보정 $Z^{corr}_{ch}$ 등급을 둘 다 계산한다.
  - 후보판: 원시로 등급, 다르면 "격자 위상 의존" 표시.
  - 이 초안 제안: **둘 중 하나라도 `ZA-2`이면 `ZA-2`**(보수 쪽), 다르면 "격자 위상 의존" 표시.
  - 이유: 격자 시험에서 원시 침하가 0.01 대 0.005 m로 RL +2.74 mm 달랐다(`b1_gridconv_judgement.md`). 문턱 3 mm와 같은 크기라 원시 하나로는 격자 몫과 크리프 몫을 가를 수 없다. `ZA-2`의 효과는 하네스 침하 항을 Chrono 쪽(깊게)으로 보정하는 것이라 행정 예산 쪽으로 안전하다.
  - terramechanics TR-1 답을 본 뒤 정한다.
- D-c·D-e의 원시·보정 병기, 대체 범위, 절점 계단 표시는 후보판 그대로다(비교 꼴은 4.1).

### 5.2 예측자 P-A의 $m_L$ (바뀜, Δ-5·Δ-6)

$$m_L = c^{\ast}_{run}(t_L) - c^\ast,\qquad c^{\ast}_{run}(t_L) = \text{마지막 LOC 주기까지 나온 } \texttt{INFO\_LOC\_CLEARANCE\_MARGIN:<mm>} \text{ 또는 } \texttt{INFO\_LOC\_FLAT\_SOIL\_MARGIN:<mm>} \text{의 마지막 값}$$

| 기호 | 정의 | 단위 |
|---|---|---|
| $c^\ast$ | `thresholds.clearance_target_m` = 0.05 | m |
| $c^{\ast}_{run}(t_L)$ | 실행 틈 목표. 두 사건이 모두 없으면 $c^\ast$ | m |
| $m_L$ | P-A에 넣는 여유 | m |

- 근거(코드 읽기): 한 LOC에서 E3c10이 켜지면 R4c30은 평가하지 않고, 실행 목표가 이미 있으면 R4c30이 켜지지 않는다. E3c10은 한 실행에 한 번이고 LOC 취소 뒤에도 남는다(`c2.py:8964-9013`). 그래서 두 사건 가운데 마지막 값이 그 실행의 목표다.
- 사건 문자열의 정수 mm는 표시값이다. 경로 1·2는 정수 mm를 m로 바꿔 쓰고, `result.json`의 제어기 상태(`clearance_target_m`)가 있으면 그 값과 1×10⁻⁹ m 안에서 같은지 본다. 다르면 그 행의 D-d는 `NA`이고 이유를 적는다.
- H-M0: `margin_m = 0`, `enable` 유지. 기대 사건은 `INFO_LOC_CLEARANCE_MARGIN:50`(E3c10 조건이 맞은 LOC). R4c30 사건이 나오면 H-M0 짝은 $m$ = 0 짝이 아니므로 D-f 계산에서 빼고 적는다.

### 5.3 M-12 LOC 앵커 기록 (새, 등급에 쓰지 않음, U-4)

- 배경: LOC 틈 추정 앵커는 평탄 창 시작 $t_P$ 주기의 0.1 s 원시 기울기 한 표본을 쓴다. 균일 연약 지면에서 그 영향은 낙관 ≤ +2.7 mm, 비관 ≥ −5.5 mm였다(`loc_anchor_review.md` 0절). P-A의 $(c^\ast + m_L - \hat c(t_L))^+$ 항에 그대로 들어가고, D-d 문턱 10 mm와 같은 자릿수다.
- 기록 항목(LOC마다)
  - 경로 ①/②/③(검토 2절 정의), $c_{min}(t_P)$, $t_P$·$t_L$의 정수 주기
  - 현행 $\hat c(t_L)$(제어기 값)과 안 A 그림자 $\hat c_A(t_L)$(중심 1 s 원시 기울기 평균, $w = \min(0.5, t_L - t_P)$ s), $d = \hat c - \hat c_A$
  - 예측자 변형 P-A\*(P-A에서 $\hat c$ 대신 $\hat c_A$)의 $e$, $E_{\text{P-A*}}$
- 하네스: 3.2 그림자 기록에서 읽는다. Chrono: 러너에 그림자 훅이 없으므로 `record.npz`의 IMU 원시 기울기(100 Hz)로 사후 재구성한다. 필드가 없으면 `NA`(행 상태는 바뀌지 않는다). 필드 존재는 G-S 건조 실행에서 본다.
- 판정서에는 D-d 표 옆에 $E_q$와 $E_{\text{P-A*}}$, $\max\lvert d\rvert$를 나란히 적는다. $\lvert E_{\text{P-A}} - E_{\text{P-A*}}\rvert$ > 5 mm이면 "앵커 단일 표본 의존"을 붙인다(표시만).

## 6. 빈 집합 관문

### 6.1 이어받음

후보판 3.1(행 상태 `VALID`/`MISSING`/`MISSING_START`/`NO_LOC`/`INVALID`)과 3.2(`COMPLETE`/`PARTIAL`/`UNDETERMINED`, 핵심 4행 C1·C2·C4·C5, 하네스 H-P VB e0 짝 5개, 계산 행 0개인 등급은 `NA`)를 그대로 쓴다.

### 6.2 더하는 것

| # | 조건 | 처리 |
|---|---|---|
| E-1 | 하네스 28실행 가운데 meta가 없거나 태그가 2.1과 다른 줄 | 그 줄은 없는 것으로 센다(통과로 세지 않는다). H-P VB e0 짝이 빠지면 묶음 `UNDETERMINED` |
| E-2 | 6.3 상수 $\kappa_{z,F}$·$\kappa_{z,R}$·$\delta_{allow}$를 계산할 다리·실행이 0개 | 상수 `NA` → P-B·P-C `NA`. D-d는 P-A만으로 내고 "후보 축소"를 적는다 |
| E-3 | D-f의 H-M0 C5 짝이 5.2에 따라 빠져 0개 | D-f = `FUP-NA`가 아니라 `NA`(계산 불가)로 적는다 |
| E-4 | M-12가 모든 LOC에서 `NA` | 표시 없음, "M-12 기록 없음"만 적는다(등급 영향 없음) |
| E-5 | 러너 로그 단계별 `errors N` 합 > 0이고 `errors_left` > 0 | 판정 전 차단(7절 I-12) |
| E-6 | 도구가 선택한 행 수가 0인데 등급이 나옴 | 도구 결함. 판정 후 감사 E에서 차단 |

### 6.3 태그로 행 고르기

- 도구는 묶음 이름(`V5-B1-CREEP`)과 행 ID(C1~C6)로 행을 고른다. 태그로 고르지 않는다. 태그는 정체성 확인(I-3·I-9)에만 쓴다.

### 6.4 이름 겹침 (새)

- 이 규칙의 "B1"은 **LOC 때 예상 최대 행정으로 E3c10 경사 틈 여유를 줄이는 설계 과제**다. 다음과 다르다.
  - 명세 426.9.B1(연구 B 운용 중량 ×1.1, 2026-10-30)
  - 3단계 H-7의 "B1"(센서 오차 행 대체 고유분 기준, 개정 7)
  - 2026-10-26 P2 해석 보완 B1~B5
- "K1"은 R4c30 순서 관문(`flat_soil_margin_order_gate`)이다. touch-phase K1(탈락)과 하네스 키 토큰 `K1`(크롤러 강성 ×1)과 다르다.

## 7. 실행 정체성

후보판 4절 I-1~I-9를 그대로 두고 아래를 더한다.

| 코드 | 조건 | 출처 |
|---|---|---|
| I-10 | 시작 직전·끝난 직후 `git rev-parse HEAD`와 `git status --porcelain --untracked-files=no`가 같고 추적 변경 0. 실행 중 그 checkout에 병합·checkout 없음(전용 worktree면 그 worktree 기준) | prelaunch, postrun |
| I-11 | C6 제어기 질량 = YAML 명목(배율 누수 없음), 플랜트 질량 = 명목 × 1.1 | C6 `result.json` |
| I-12 | 러너 로그 단계별 `errors N` 비영이면 `errors_left` = 0일 때만 진행, 첫 시도 오류는 판정서에 기록 | `tools/verif/log_errors.py` |
| I-13 | 추적 파일에 `{이름}` 자리표시 없음. prelaunch 값은 추적 밖(배치 폴더)에 채움 | `tools/verif/placeholder_scan.py --allow` |
| I-14 | 실행 셸에서 지운 env와 더한 env 목록, 인터프리터 플래그(`-I` 포함) | prelaunch `env_removed`·`env_set`·`interp_flags` |
| I-15 | 실제 argv와 rc를 러너가 아닌 래퍼가 `batch.json`에 남김(`s9_batch` 경로가 아니면) | `batch.json cases[].argv/rc` |
| I-16 | G-S 건조 실행 기록(3.4)이 본 실행보다 앞섬 | prelaunch `dry_run` |

- 실행 전 기록 초안: 같은 폴더 `b1_creep_prelaunch_draft.md`.

## 8. 두 경로 판정

- **필요하다.** 후보판 8절 그대로: 경로 1 = python-expert 도구(`b1_creep_metrics.py` 가칭, 실행 전 감사 전에 sha 고정), 경로 2 = control-expert 독립 스크립트(경로 1 코드·출력을 보지 않음, numpy·json만, Chrono 결과 전 sha 고정, 하네스 짝으로 시험).
- 대조 K-R 항목에 더한다: 5.2 $m_L$, 5.3 M-12 전 항목, 4.1 비교 꼴의 분류 결과(각 문턱마다 행별 앞/뒤), 4.2 정수 주기.
- 값 대조 허용: 이산 항목 완전 일치, 실수 절대차 ≤ 1×10⁻⁹ m(후보판 그대로). **문턱 비교 허용 $\varepsilon_{th}$(4.1)과 섞지 않는다.**
- 불일치면 그 항목이 들어가는 등급은 `UNDETERMINED`, 도구를 결과에 맞춰 고치지 않는다(후보판 그대로).
- 경로 2 작성자는 경로 1의 코드·출력을 보지 않는다. 정렬은 이 규칙의 문장으로만 한다(메모리 two-path-independence).

## 9. 사전 예측 (등급에 쓰지 않음)

- P-1~P-9: 후보판 7절 그대로.
- 새 예측(이 초안, 결과 전)

| # | 예측 | 근거 |
|---|---|---|
| P-10 | B1 Chrono·하네스 LOC의 앵커 경로 ②는 0건. 모든 LOC에서 $\lvert d\rvert \le$ 5.5 mm, $d$ > 0(낙관)은 ≤ +2.7 mm | 검토 0절(균일 연약 지면 범위), H-SH ② 0줄 |
| P-11 | ×1.0 C1~C5에서 R4c30 사건 0, `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order` 0(정착 기울기 > 1°라 R4가 평가되지 않음). $m_L$은 0.03 또는 0 | 바닥 2.8°·대각 1.925°/1.4° |
| P-12 | H-M0 4실행의 E3c10 사건 값은 모두 50 mm 또는 사건 없음, R4c30 사건 0 | 5.2 |
| P-13 | G-S 건조 실행은 처음 시도에서 정체성·필드 검사를 모두 통과하지 **못할** 수 있다(격자 기록 R-G1~R-G3, M-4h 필드가 아직 구현되지 않음, 13절 R-7) | grep 2026-11-11 |

## 10. terramechanics-expert 검토 필요 (봉인 전)

사용자 결정: B1 문턱(3 / 5 / 10 / 20 / +5 mm)은 봉인 전에 terramechanics-expert 검토를 받는다.

- 기록상 사실: 후보판 0.3·12절 R-6은 2026-11-10 검토 뒤 "문턱 그대로(사용자 결정)"로 닫혔다. 그 검토는 **격자 시험 결과(같은 날 저녁 `PASS`, 원시 차 RL +2.74 mm·FL −0.80 mm) 전**이었다. 이 초안은 그 뒤 새 자료로 다시 볼 항목만 묻는다(U-2).

| # | 질문 | 관련 문턱·식 | 새 자료 |
|---|---|---|---|
| TR-1 | D-a 3 mm를 원시 침하로 재는 것이 격자 위상 몫($\lvert f-1\rvert z$, 절점 계단 후방 약 1.0 mm)과 가를 수 있는 크기인가. 원시·보정 보수 쪽(5.1 제안)이 맞는가 | T-1, 5.1 | 격자 시험 원시 차 RL +2.74 mm |
| TR-2 | D-b 5 mm: SCM 점성 지연 $\tau = R/(n\,p/z)$ ≈ 0.4~0.5 s 동안의 침하가 $\delta^{os}$(READY → $t_{\max}$)로 들어가는가, $\Delta z^{post}$로 들어가는가. $t_{\max}$ 정의가 맞는가 | T-2, M-5 | — |
| TR-3 | D-d 10 mm와 패드 종류별 선형 $\kappa_z$: $n$ = 0.2에서 접선 유연도 ∝ $F^{4}$이면 ×1.0 안의 하중 차(다리마다 다름)에서도 선형 상수가 10 mm 안에 들 수 있는가 | T-4, 후보판 6.3 | — |
| TR-4 | D-e 20 mm: 명목 세트의 가드 여유 20 mm를 "B1 재확인"으로 읽어도 되는가($k_{eq}$ 4 %·$n$ 0.02로 20 mm 이상 변함, $p/q_{ult}$ 0.82~0.87) | T-5 | — |
| TR-5 | D-g +5 mm: ×1.1 침하 1.61배에서 고정 +5 mm가 적절한가, 비례 꼴이 나은가 | T-6, P-9 | — |
| TR-6 | 경사 2.8° J2에서 패드 기울기·미끄럼으로 $f$가 실행 중 바뀌는 크기. M-11 기록 간격 1.0 s·$N_h$ ≥ 3이 충분한가 | T-7, M-4h | 격자 시험은 위상 0 한 점·단일 패드 |
| TR-7 | 크리프 정지 기준(1.0 s 창 < 0.1 mm/s)이 점성 모형에서 정착을 뜻하는가(P-2) | T-12 | — |
| TR-8 | $Z_{soil}$(T-2, 실토양 크리프 허용) 답. 이 규칙 등급에는 안 쓰고 B1 설계 문서에서 쓴다 | 후보판 R-5 | 아직 없음 |

- 답에 따라 문턱 값이 바뀌면 봉인 전 변경이고 15절 변경 기록에 적는다. 결과는 아무것도 보지 않은 상태여야 한다.

## 11. 비용 추정 (가정)

| 항목 | 벽시계 | 근거 |
|---|---|---|
| Chrono C1~C5 | 행당 7,000~10,000 s(P, threads 4, fast) | 후보판 11(REM 상단 6,500 s × 160/120, 경사 ±15 %) |
| Chrono C6 | 9,000~12,500 s | 후보판 11 |
| 격자 기록 R-G1~R-G3 | ≤ +5 % | T-10 |
| E 풀 배율 | × 1.5 | SCM 실측(CLAUDE.md) |
| 6행 묶음 | P 4 + 2(두 물결) 약 4.5~6.3 h | 후보판 11. 풀은 Q4 |
| G-S 건조 실행 | Chrono 2행 × 10 s 시뮬레이션(초기화·정착 포함) 약 10~20 분 병렬, 하네스 2실행 수 분 | 가정(SCM 약 55 s/시뮬레이션 s 외삽) |
| 하네스 28 + 그림자 끔 짝 4 | E 4~8 워커 약 15~25 분 | 후보판 11, H-SH 줄당 1.2~4 분 |
| 경로 1·2 재집계, M-12 사후 재구성 | 각 수 분 | — |
| 전체 | P코어 약 5~7 h(Chrono가 지배) | — |

## 12. 순서와 감사 시점

```
P5r4+K1 판정·채택 결정 → (전환 있으면) 전환 후 감사
→ terramechanics 재검토(10절) → 사용자 결정 U-1~U-7 → 원판(합친 판) 작성·파라미터 채움 → 봉인
→ 구현(cad 행·격자 기록·필드, python 경로 1·하네스 지원) → 경로 2 작성·sha 고정(하네스 짝 시험)
→ 하네스 28(+짝 4) → 상수 고정(b1_harness_constants.json sha) → G-S 건조 실행
→ 실행 전 감사(차단 0) → prelaunch(추적 밖 채움) → Chrono 6 → postrun
→ 경로 2 → 경로 1 → K-R 대조 → 등급 → 판정서 → 판정 후 감사 → integrity → 커밋
```

- P코어 순서(후보판 11절을 고침): P5r4+K1 Chrono 12행 → 판정·채택 결정 → 이 6행. D8x Chrono 19행은 B-G1 미달로 실행하지 않았다.
- 436.8은 B1 다음이다(decision_log 11-11). 이 6행은 436.8과 P코어를 다툰다. 배치는 compute-scheduler-expert가 정한다.
- 감사 범위는 후보판 9절에 I-10~I-16, 4.1 비교 꼴 전수, 3.3 겹침 표 대조를 더한다.

## 13. 남은 확인 (후보판 12절 상태 갱신)

| # | 상태(2026-11-11) | 누가 |
|---|---|---|
| R-1 파라미터 | 열림. K-2 갈래 없어짐, P5r4 결정 대기 | 사용자 → 메인 세션 |
| R-2 `--start-limit`·지형 크기·M-4h 필드 | 열림. 권고 `record_only` | cad-expert |
| R-3 6.1 기하 부호 | 열림 | dynamics-expert |
| R-4 하네스 질량 배율·$m$ 교체 | 열림. `run_v5.py`에서 `mass_scale` 못 찾음. $m$ 교체 꼴은 5.2로 정함 | python-expert |
| R-5 $Z_{soil}$ | 열림(TR-8) | terramechanics-expert |
| R-6 문턱 | **다시 엶**(10절, U-2) | terramechanics-expert → 사용자 |
| R-7 격자 기록 R-G1~R-G3 | 열림. `03_src`·`04_scripts`에서 구현 흔적 못 찾음(grep) | cad-expert |
| R-8 경로 1 M-11·D-c 이중 등급 | 열림. M-12·4.1 비교 꼴·5.2 $m_L$을 더함 | python-expert |
| R-9 격자 시험 | **닫힘**(`PASS`, `a483ac48…`) | — |
| R-10 하네스 연속 Bekker | 열림 | python-expert |
| R-11 저장 경계 행 위상 재구성 | 닫힘(별도, `evidence/grid_phase/`, 11-10 결정) | — |
| R-12(새) M-12 Chrono 입력 필드(IMU 원시 기울기 100 Hz) 존재 | 열림 | cad-expert |
| R-13(새) H-M0 `margin_m = 0` 연구 하위 클래스, 그림자 훅 하네스 연결 | 열림 | python-expert |

## 14. 가정

- 후보판 13절 전부.
- 이 초안에서 정한 값: $\varepsilon_{th}$ = 1×10⁻⁹ m, $\varepsilon_F$ = 1×10⁻⁶ N, T-8 연속 100표본, M-12 표시 문턱 5 mm, G-S 건조 실행 10 s와 대상 꼴 2개, 11절 건조 실행·그림자 비용, P-10~P-13.
- 안 A 그림자 창 $w = \min(0.5, t_L - t_P)$ s는 `loc_anchor_shadow.py`의 `MAX_HALF_WINDOW_S`와 같다(코드 읽기). 경로 2는 이 정의를 문장에서 다시 구현한다.

## 15. 변경 기록 (봉인 전)

- 2026-11-11 초안 v2 작성(control-expert, 결과 전). 후보판(`7c782632…`) 대비 1절 Δ-1~Δ-14. 후보판 파일은 고치지 않았다. B1 결과와 P5r4+K1 결과는 보지 않았다.
