# 436.8 경로 2 독립 재집계 도구 (`p2_4368.py`)

- 규칙: 원판 `../../v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1 `../../v5_resume_4368_rules_rev1.md`(`d9094fda…`), rev2 `../../v5_resume_4368_rules_rev2.md`(`497e4614…`). 앞 판과 다르면 뒤 판을 따른다. 세 파일의 sha256과 `.sha256` 기록, LF·BOM 없음을 실행할 때마다 확인한다. 봉인 규칙 파일은 raw sha만 쓴다. 하나라도 어긋나면 **종료 2(S-1)**로 멈춘다. 부록 A 33개 파일도 확인한다. raw가 다르고 CRLF→LF로 바꾼 sha만 같으면 통과로 둔다(rev2 R2-9). 그 파일은 출력 `seals.eol_only_detail`에 raw·LF sha와 "CRLF 변환만 다름"을 적는다(판정서 공개용).
- 작성자: dynamics-expert(경로 2, 사용자 결정 2026-11-13). 경로 1 도구와 그 출력은 보지 않았다(규칙 9.2). 읽은 것은 아래 "독립성 공개"에 있다.
- 환경: `conda run -n dynamics-dev python -I -B p2_4368.py ...`. 표준 라이브러리와 numpy만 쓴다(npz 읽기). 프로젝트 모듈 가운데 import하는 것은 `v5_options.is_extend_start_tag` 하나다(규칙 4.1이 ③ 판별을 이 함수로만 하라고 정한다).
- 공통 CLI: `--repo <루트>`(기본은 이 파일에서 다섯 단계 위), `--out <JSON>`. 종료 코드는 0(멈춤·실패·판정 불가 없음), 1(실패, 판정 불가, K-10 차이), 2(멈춤 S-*, 규칙 sha 불일치), 3(도구 오류)이다. stdout 마지막 줄은 JSON 요약이고 `tool_sha256`, `status`, `exit`, `out_sha256`, `stop_codes`를 담는다.

## 하위 명령과 규칙 절

| 하위 명령 | 입력 | 규칙 절 | 내는 것 |
|---|---|---|---|
| `seal` | – | 머리, 3 A-2, 8.2 S-1, 부록 A | 규칙·rev1·부록 A sha |
| `harness --manifest m.json` | 하네스 출력 파일 목록 | 4.1, 4.2, 5.1, 7.2, 9.3, RV1-2·3·6·9·12 | 묶음별 줄 수, 태그 표, 계열 표, K1 분류 표, 저장 해시 대조, 멈춤·판정 불가 목록 |
| `anchors [--h1 h1_d1.jsonl]` | 저장 앵커 5개(부록 B sha 확인) + H-1 | 10 P-1·P-2, RV1-5, S-7 | 앵커 선택 수(8/184/216/165/291), P-1 408줄·P-2 456줄 해시 대조 |
| `chrono --batch D [--batch D2 …] [--gs] [--check-counts] [--c2-expected N] [--c2-psc N]` | Chrono `batch.json` + 행 결과 | 4.1, 4.2, 5.2, 6, 7.2, 7.4, 9.1 C-8, 11.2, RV1-10 a·b·f·g·h | 행별 태그·금지 인자·기록 확인·정체성·K1 분류·$R_c$·1 ms 재계산·O-C5 등급, 시작 조건 밖 행 목록 |
| `oc5k --row C-8a\|C-8b --probe p1.json [--probe …]` | probe `result.json`(시작 조건 키·바닥 인자·`duration`만 읽음) | 5.4-3~8, RV1-10 d·e, S-10 | 축척 $k$ 순서, 바닥 각, probe 수 |
| `jp --shadow shadow_jp_b0.jsonl --batch <V5-JP-VB> --batch <V5-JP-V0>` | 저장 J_P 12행 `controller_events.json` | 7.3 | 조건 1·2와 재사용 여부 |
| `openloop --run LABEL=<run_dir> […]` | 열린 루프 `result.json` + `series.npz` | 5.3, 7.5, 9.1 C-6·C-7 | `openloop_compare.py`의 `analyse` 값, 명세 11047 FLAG, 경로 2 가정 속도비 |
| `compare --a A.json --b B.json [--map map.json]` | 확정된 두 출력 | 9.2 K-10 | 차이 목록 |

### harness 목록 파일 꼴

```json
{"files": [
  {"bundle": "H-1", "path": "06_analysis/03_hydraulic/coupled/v5/resume_k1/h1_d1.jsonl",
   "format": "run_v5_jsonl", "kind": "V0", "expect_lines": 434},
  {"bundle": "H-10", "path": ".../h10_reuse_rerun.jsonl", "format": "run_v5_jsonl", "kind": "VB",
   "stored": "06_analysis/03_hydraulic/coupled/v5/main.jsonl"}
]}
```

- `format`: `run_v5_jsonl`(줄 최상위 `resume_k1`), `u3_json`(`records[].v5.resume_k1`), `r79_json`(`results[].resume_k1`), `grid_json`(`results[i].runs[j].resume_k1`).
- `kind` → 기대 태그(규칙 4.1, RV1-3.2): `V0`·`V0v`·`S6SEED`·`V3`·`H7`·`NOP3` → `final_C4G2_LAS_K1`, `VB`·`LS`·`H6` → `final_C4G2_P3_LAS_K1`, `ABL` → `ABL_LAS_K1`, `IND` → `IND`, `IND_LAS` → `IND_LAS`. 한 파일에 두 판이 섞이면 행마다 S-2가 난다. `H6`·`H7`이면 `two_pressure.extend_start_rule`도 본다(키가 없으면 기록만).
- `stored`(선택): 미작동 줄의 명령 해시를 대조할 저장 파일(규칙 7.2 "저장 행 해시"). 어느 저장 파일이 앵커인지는 판정서가 정한다. H-1은 `stored` 대신 `anchors`를 쓴다.
- 묶음 줄 수는 rev1 값(H-1 868, H-3 2,228, H-4 968, H-5 14, H-6·H-7 각 135, H-8 3,106, H-9 1,676, H-10 440)과 대조한다(S-15). H-4의 IND와 IND_LAS 파일은 각각 242줄이어야 한다.

## 정의 (경로 2가 규칙 문장에서 정한 것)

| 항목 | 경로 2 정의 | 근거 |
|---|---|---|
| 줄 키 | run_v5: `job`에서 `mask`·`t4h_dir`를 뺀 정렬 JSON. 그 밖: `key` → `id` → `case`, `controller`가 있으면 `\|<controller>`. 격자 run: 부모 `key` + `\|runs[j]` | 입력 키 사실, RV1-5 |
| K1 막힘 | `decisions` 항목에서 `would_block` ∧ `r4_due_without_gate` | 7.2 |
| 미작동 | LAS-b `start_s`가 None(키가 없어도 None) ∧ 모든 `would_block` 거짓 | 7.2, 입력 키 사실 |
| `would_block` 참 ∧ `r4_due` 거짓, 또는 `applied` 참 ∧ `r4_due` 거짓 | 기록 모순: 그 줄은 `판정 불가`, 묶음은 **S-5** | rev2 R2-1 |
| `_SKIPPED:order` 수 | 줄 `events`(전체 목록일 때) → `event_names` 개수 → `resume_k1.event_counts.flat_soil_margin_skipped_order` 순. Chrono는 `events[]`, 없으면 `controller_events.json`. 이름 완전 일치 | 7.2, 7.3-3 |
| 지면 계열 | `@`가 든 토큰(패치 `토양@다리`, 처방 침하 `c-mid@다리`) → 패치·처방. `rigid` 토큰 → 강체. 토양 이름(G1·G5·J1·J2·S1·S2)만 → 균일 연약. 그 밖 → 미분류. D-1은 `job.d1`의 `base`·`patch_leg`·`patch_soil`·`sink`를 먼저 본다. Chrono: L2b·L1-R → 강체, `rigid_base`·`soil_patch` → 패치, `soil`만 → 균일 | 7.2, RV1-6(경로 1 계열 표는 쓰지 않음) |
| 미분류 + K1 막힘 | 균일과 같게 S-6 | RV1-6, rev2 R2-7 |
| 격자(r67·r69) run | 파일 `meta.spec` = `rev. 67 (G1 / G2 / G7 reduced screen)` ∧ run `event` ∈ {G4, RE1bF, FS24} → 패치·처방, 그 밖 → 미분류(균일로 다룸). 키 문자열은 쓰지 않는다 | rev2 R2-7 |
| LAS-b `start_s` | 블록이 있고 키가 없거나 None → 시작 안 함. 블록이 없으면 판정 불가. C-4 끔 팔은 'LAS 없음' | rev2 R2-2 |
| `applicable` 거짓 | IND·IND_LAS에서는 "해당 없음"으로 세고 분류·4.2 확인을 하지 않는다. 다른 종류 줄이면 S-3 | RV1-6 덧붙임 |
| LAS-b 설정 9값 | `enable` True, `sum_on_fraction_W` 0.6, `light_leg_fraction_of_F_min` 3.5, `slow_mean_fraction` 0.16, `sum_off_fraction_W` 0.85, `off_periods` 5, `max_s` 1.5, `rho_on` 0.18, `require_soil_response` True(ABL은 False). 키 `min_active_periods`·`end_ramp_periods`가 있으면 0이어야 한다(P0) | 4.2, 명세 436 설정 표 |
| L2b·L1-R 4.2 확인 | 요청 = argv(`--k1-order-gate`가 없으면 `preset`, 있으면 S-3), 적용 = `controller_meta.slope_clearance_margin.order_gate.enabled`. `controller_meta`나 그 키가 없으면 판정 불가 + S-3 | rev2 R2-3 |
| 이탈 시각 $t_d$ | `step_series.npz`의 `scm_crawler_normal_N` < 0.01 `p3b.weight_N`이 0.1 s 이상 이어지는 첫 구간의 첫 표본 | `p3b.departure.rule` 문자열(P3a-2) |
| $F^{a}_{min}$ | $t \ge t_d$의 1 ms `F_cyl_N` 다리별 최소 | 2절 기호 표 |
| $F<F_{min}$ 시간, $F<F_{min}$+2 kN 시간 | $t_D$ = `step_series.npz` `scm_crawler_normal_N` < 0.01 `p3b.weight_N`이 0.1 s 이상 이어지는 첫 구간의 첫 표본. 창 $[t_D, t_D + 8\,\mathrm{s}]$(실행이 먼저 끝나면 `window_truncated_at_run_end`) 안의 표본 수 × $\Delta t$. 다리별 값과 네 다리 최대를 낸다. $t_D$ 뒤 실행 끝까지의 전체 창 값은 기록만 한다. $t_D$가 정의되지 않으면 판정 불가. 저장 P5r4 A1·A3·A5에서 $t_d$·RL 최소·두 시간이 판정서 8.2 표와 같다(0/131, 195/362, 67/161 ms) | rev2 R2-5 |
| O-C5 $m$·멈춤 | $R_c \le 1$일 때 경로 2 $m$(1 ms, $t \ge t_D$ 다리별 최소의 최소)으로 처리 칸을 낸다(멈춤 / 여유 기록 / 기록). `result.json` 최소로 정한 칸도 함께 낸다. 어느 쪽이든 $m < F_{min}$이면 S-9이다. 두 경로 칸이 다른지의 비교는 판정서에서 한다 | 7.4, rev2 R2-6 |
| $R_c$ | 기록된 `crawler_attitude_deg`로 $\lvert\phi_c\rvert/4.4 + \lvert\theta_c\rvert/3.2$ 재계산. 기록값과 K-10 허용 밖이면 기록 | 2절, 9.1 C-8 |
| 열린 루프 | `openloop_compare.py`의 `first_run`·`plane_fit`·`analyse`와 상수만 AST로 꺼내 실행한다(모듈 끝의 저장 행 실행은 하지 않음). 속도비 두 가지: `r_vu` = 다리별로 `flow_series.npz` 1 ms 행 가운데 8.5 s < t ≤ 끝 ∧ u ≥ 0.1 v_max인 행의 v/u 중앙값(P-10 대조, V0는 해당 없음). `r_v` = 10 s ≤ t ≤ 20 s 구간 첫·끝 표본의 `s_motor` 차 / 시간 / v_max(P-11·P-11b 대조). v_max = YAML `actuator.max_speed_m_s`. 저장 J1 VB_prop `r_vu` 0.8947 × 4, J1 VB_FB `r_v` 0.8769로 판정서 값과 같다 | rev2 R2-4 |

## H-1·H-2: `p2_d1.py` (원 규칙 `d1_selection_rules.md` + rev1)

- 실행: `conda run -n dynamics-dev python -I -B p2_d1.py --h1 <resume_k1/h1_d1.jsonl> --out <x.json>`. 실행할 때마다 436.8 원판·rev1·부록 A sha와 D-1 규칙 두 파일 sha를 확인한다. 핵심 함수는 `p2_4368.py`에서 가져오므로 출력에 두 파일 sha가 모두 찍힌다.
- 종료 코드(원 규칙 12절과 같은 뜻): 0 = 선별 완료, 1 = 관문 G-1·G-3·G-4 멈춤 또는 교차 확인 차이, 2 = G-2 입력 누락 또는 규칙 sha 불일치, 3 = 도구 오류.
- 경로 2가 다시 세는 것:
  - 관문 G-1~G-4(10절). G-1은 H-R 105조합·420실행, H-S 106·424, H-S-C-g 6·24로 대조한다.
  - 여유 $m$(4.1). $T_{lim}$은 rev1 1절 문장으로 경로 2가 다시 정하고, 기록된 `t_ready_limit_s`와 다르면 실패로 적는다.
  - 후보 등급·$m$과 순위·동점(4.2·4.3), 기준선 실패 둘째 행.
  - S1(5절), S2(6절, fup-rec 제외 규칙), S3 촉발 T1~T3(7절).
  - 8절 크롤러 ×3 규칙(전체 $m$과 항별).
  - C-2 행 수(RV1-10 g의 S-15 대조값: `C2_selected_rows.n_rows_selected`, `n_psc_rows`).
- 실행 등급: 순위에는 3절 입력 `d1.verdict`를 쓴다(선별 규칙이 이 필드로 정의돼 있다). 경로 2는 11절 H-R 항목 가운데 기록된 하네스 값으로 정의되는 다섯 항목을 다시 판정해 기록 등급과 대조한다. 다섯 항목은 이륙 뒤 1 ms 최소 ≥ $F_{min}$, 끝 자세 ≤ 0.2°, READY ≤ 한계, 이동 ≤ 180 bar, FAULT 0이다. 어긋나면 실패로 적는다(436.8 S-13 후보). H-S의 P3·G6·E 항목과 H-R의 잠김 350 bar·G6 항목은 기록 값에 판정 정의가 닫혀 있지 않아 다시 판정하지 않는다(확인 필요 D-4).
- 동작 확인(판정 아님): 저장 기준선 `v5/d1.jsonl`(LAS-b 전, 868실행)에 돌렸다.
  - 교차 확인 차이 0, READY 한계 차이 0이었다.
  - G-3 멈춤 1건 `D1|H-R-A|rigid+J1@FR|T|diag-op|K1`이 나왔다. 436.8 P-4가 적은 옛 G-3 정지 행과 같다.
- 시험 `test_p2_d1.py`(11개)는 원 규칙 12.1 봉인 시험값 #1~#8과 관문·교차 확인을 다룬다.

## H-3·H-4: `p2_u3.py` (원 규칙 `u3_u6_rerun_rules.md` + rev1 + rev2, 436.8 7.1 rev3 몫)

- 실행: `p2_u3.py --u3 V0=<las_k1/u3_x_V0.json> --u3 VB=<…_VB.json> [… 묶음 파일 전부] --u6 ALL=<u6_b5_wide_VB.json> --u6 ALL=<u6_b5_main_VB.json> --u6 IND_LAS=<…_VB_IND_LAS.json> --h1 <resume_k1/h1_d1.jsonl> --out x.json`. 실행할 때마다 436.8 sha와 u3_u6 규칙 세 판 sha를 확인한다.
- 종료 코드: 0 = 이상 없음, 1 = 등급 판정 불가 또는 G-5(VB 고유 실패, 묻기), 2 = 관문 G-1·G-2·G-4·G-6 또는 규칙 sha 불일치, 3 = 도구 오류.
- U-3에서 다시 세는 것:
  - G-1: 키 1,114 × V0·VB. suite 이름이 원 규칙에 있는 묶음은 suite별로 센다(slope 110, h6 26, h9 24, g6 116, g8 516, p3b 171). 나머지 suite는 합 151(연구 B 84 + C 34 + D 33)로 센다. V0·VB 키 집합이 같아야 한다.
  - G-2: v5 meta 6칸과 태그. 한 파일 안의 태그가 하나여야 한다.
  - G-4: VB 실행을 태그가 아니라 파일 설정으로 고른다. 헤드 전용 묶음은 `no_rod_reading`·선언 있음·로드 판독 없음이어야 하고, g8은 로드 판독 있음·J-P3 `pass`여야 한다. 고른 수가 0이거나 VB 키 수와 다르면 멈춘다.
  - G-6: g8 VB의 로드 대체 사건이 0이어야 한다.
  - 5.1: 4×4 등급 이동표, VB 고유 실패(G-5), 기준선 실패, VB 개선, 통과↔안전 종료, 다섯 가지 차, 묶음 문구 개수.
  - 6절 D-1 재사용: eps 0·같은 설정의 D-1 줄 1개, 태그 승계, 명령 해시가 같은지.
- U-6에서 다시 세는 것: 제어기별(C2·ABL·IND, 기록 열 IND_LAS) 사례 수 242, lite 통과 수, 공식 판정 분포, C2 안전 종료 수, `crawler_liftoff_fail` 수, 태그(③은 C2만), IND_LAS ↔ IND 명령 해시가 같은 수.
- 등급 사상(경로 2 정의):
  - `verdict` `pass`이고 `flags`가 비어 있음 → 통과
  - `pass`이고 `flags`가 있거나 `late_loc_reapproach.is_flag` 참 → FLAG
  - `stroke_limited_stop` → 안전 종료(`soil_stop.pass` 거짓이면 실패)
  - `fail` → 실패
  - 그 밖(`settle_check_fail` 등) → 판정 불가(확인 필요 U-1)
- 다시 세지 않는 것: G-3(옵션 없는 경로 동일성)은 추가 실행이 필요해 이 도구 몫이 아니다.
- 시험 `test_p2_u3.py`(6개).

## v5 J 항목과 H-5: `p2_v5j.py` (v5 기준 원판 + 개정 1~12b, `u9_targeted_rules_rev1`)

- 작성: dynamics-expert(경로 2 둘째 작성자, 2026-11-13). 앞 작성자의 `p2_4368.py` 공통 함수(봉인 확인, 문턱 비교, 태그 상수, `is_extend_start_tag` 적재)를 그대로 쓴다.
- 실행: `p2_v5j.py --out x.json u9 --v0 <resume_k1/h5_u9_v0.jsonl> --vb <resume_k1/h10_reuse_rerun.jsonl> [--h0-ref <같은 파일>] [--stored-main <v5/main.jsonl>] [--stored-p3 <v5/p3_hash.jsonl>] [--t4h-root <h10 T4h 폴더>]`. 실행할 때마다 436.8 sha(원판·rev1·rev2·부록 A, R2-9 LF 정규화)와 `u9_targeted_rules_rev1.md` sha를 확인한다.
- 종료 코드: 0 = 통과(분류 A·B), 1 = 분류 C(사용자 결정) 또는 판정 불가, 2 = 멈춤(H0, S-2 태그, S-15 키, H-7·H-9, J-P3 설정 결함) 또는 규칙 sha 불일치, 3 = 도구 오류.
- `--vb` 파일에서 `job.setting` = VB ∧ `job.u9_metrics` 참인 줄만 U-9 VB로 고른다(η_v 0.85·0.80 각 14). H0 ①의 기준 줄은 `--h0-ref`(기본 `--vb`)에서 `u9_metrics`·`eta_v`가 없는 VB 줄 가운데 같은 (사례, ε)다. 436.8에서는 p3_hash를 따로 돌리지 않으므로(RV1-2) H-10의 main VB 줄이 그 기준이다(확인 필요 U9-a).

### J 항목 읽기 (경로 2 정의, 줄 필드)

| 항목 | 정상 행 | 사건 행(`t_event_s` 있음 또는 `event_output.pass`가 참·거짓) | 실패 |
|---|---|---|---|
| J1 | `harness_class` ∈ {pass, stroke_limited_stop}이면 통과 분류. 두 분류 사이 이동도 실패(봉인 6절 "분류가 `stroke_limited_stop`에서 벗어남") | `event_output.pass` | V0 통과, 설정 실패 |
| J2 | `values.forces.after_liftoff.min_kN` ≥ $F_{min}$(9.414589 kN, 436.8 2절). 강체 R* < 14.415 kN은 `spec_shortfall` 기록 | 강체 사건(R12·R14·R15·R16) `event_output.after_window_force.min_1ms_kN` ≥ $F_{min}$. 그 밖 사건은 토양 빠른 사건으로 보고 `min_trailing_0p5s_kN` ≥ $F_{min}$ ∧ `lift_ms_after_window` = 0 | V0 통과, 설정 미달 |
| J3 | S1~S5·S7 `values.times.t_first_ready_s` ≤ 100 s(판정), S8 READY 없음, 강체 R* 기록(R3 경사 120 s, 그 밖 평지 90 s 초과 FLAG) | 기록(복귀는 J5) | V0 안, 설정 초과·미도달 |
| J4 | `final_phase` | 같음 | V0 `ready`, 설정 다름 |
| J5 | 해당 없음 | `event_output.t_ready_back_s` ≤ 60 s | V0 만족, 설정 불만족 |
| J6 | `values.attitude.max_abs_last_5s_deg` ≤ 0.2° | `max|event_output.att_end_deg|` ≤ 0.2° | V0 안, 설정 밖 |
| J7 | `events`([t, 이름])와 값 목록의 FAULT_*·WARN_* 이름(숫자 접미사는 값으로 보고 뗌), `INFO_ROD_PRESSURE_FAULT_REASON:<다리>:<D>` 사유 | 같음 | 설정에 V0에 없던 이름·사유. 대체 시각 차는 기록 |
| J8 | `command_stats.n_rev` ≥ 2 $n^{off,max}$ ∧ ≥ $n^{off,max}$ + 6, $n^{off,max}$ = 같은 행(작업에서 설정·ε·오프셋을 뺀 키) V0 줄의 최대 | 같음 | 리밋 사이클 의심 |
| J9 | M2 켬(`hydraulic_options.m2_law`)이면 `hydraulics_record.m2_clipped_steps_post_lift` 합 > 0 → H-9 멈춤 | 같음 | – |
| J10 | `values.pressure.max_moving_bar` ≤ 180 bar | `event_output.pressure.moving_outside_max_bar` ≤ 180 bar | V0 안, 설정 밖 |
| J11 | `lock_window_alignment.n_late_fallback` > 0 → H-7. `{n_late: None, reason}`만 있으면 `not_computed`(기록) | 같음 | – |
| J-P3 | ③ 켬(`is_extend_start_tag`)만. 개정 9 3.2 표. 로드 판독 유무는 `--t4h-root`의 T4h `rod_pressure_Pa` 유한값(개정 9 3.1), 없으면 `head_only_declared`의 반대로 가정 | 같음 | breach > 0 → H-7, 표 #2·#4·#5 → 설정 결함 멈춤 |

- 판정 불가: 위 값이 없으면(9.3). J 항목의 "기준선 실패"(V0도 실패)는 실패로 세지 않고 `baseline_fail`로 적는다.

### H-5 U-9 (`u9_targeted_rules_rev1` 4절·4.1절)

| 규칙 | 경로 2 |
|---|---|
| 2절 키 | 14키 × {V0, VB 0.85, VB 0.80}. 키 집합이 다르거나 중복이면 S-15 |
| 7.1 태그 읽기 | V0 `final_C4G2_LAS_K1`, VB `final_C4G2_P3_LAS_K1`. 다르면 S-2 |
| H0 ① | VB 0.85 S2 ε 2e-3, S3·R3·S5 ε 0의 `commands_sha256` = 기준 VB 줄. 다르거나 기준이 없으면 멈춤 `U9-H0` |
| H0 ② | 나머지 ε 키를 `--stored-main` VB 줄과 같은지 기록(`--stored-p3`도 기록) |
| T1 | VB 0.85·VB 0.80 각각 V0 짝과 J1~J11 + J-P3 |
| T2·T5 | 기록(`level_count_s`, `longest_ge3_s`, `longest_eq4_s`, E1 LEVEL `short_s`, E2 LEVEL 최소 r, E4, READY 차) |
| T3a | VB 0.80 `ge3_runs` 모든 구간·축 `max_abs_delta_deg` ≤ 0.10° |
| T3b | 모든 구간·축 \|`filtered_end_deg`\| ≤ \|`filtered_start_deg`\| + 0.05° |
| T3c | `max_abs_after_liftoff_deg`(0.80) ≤ 같은 키 0.85 + 0.10° |
| T4 | E5 `back_in_band_after_saturation_s` ≤ max(20 s, 0.85 값 + 5 s), 값 None은 실패, 키 없음은 판정 불가. `max_abs_integral_rad_s` ≥ `integral_limit_rad_s`면 FLAG 기록 |
| 4.1 분류 | C: 포화 원인 실패(V0 J1 통과 ∧ 0.85 T1 통과 ∧ 0.80 T1 실패) 또는 T3a·T3b·T4 실패. T3c만이면 "C (T3c only)". 아니면 어느 키든 `longest_ge3_s` ≥ 0.5 s면 A, 모두 미만이면 B. D(0.85 T1 실패 또는 V0 J1 실패)는 따로 적고 분류는 나머지 키로 |
| 436.8 등급 | A·B → 통과, C → 미달(사용자 결정), 결측 → 판정 불가, 멈춤 → 멈춤(확인 필요 U9-b) |

- 동작 확인(판정 아님): 저장 `v5/u9_targeted.jsonl`(옛 태그 `final_C4G2`·`final_C4G2_P3`)의 V0 14줄을 scratchpad로 떼어 `--vb` 저장 파일, `--h0-ref v5/p3_hash.jsonl`, `--t4h-root v5/u9_targeted/t4h`로 돌렸다. 기대대로 태그 S-2 멈춤 42건만 나왔고(옛 태그), H0 ① 4키는 같음, 판정 불가 0이었다.
- 시험 `test_p2_v5j.py`(12개, 합성 줄): J 항목 통과·실패, 문턱 허용 1e-9, 기준선 실패, J8 두 조건, H-9·H-7·J-P3 결함 멈춤, J11 사유 기록, 이름 접미사, U-9 분류 A·B·C·C(T3c)·D, H0·태그·키 수 멈춤, 결측 = 판정 불가, 실제 u9 규칙 sha.

## H-0 T-3K: `p2_t3k.py` (`las_targeted_rules` 원판~rev5, 봉인 11개)

- 작성: dynamics-expert(경로 2 둘째 작성자, 2026-11-13). 경로 1(`las_judge`, `las_h7`, `las_t3*` 판정 부분)과 그 출력은 보지 않았다.
- 실행: `p2_t3k.py --out x.json --r0 <t3_k1/las_T3_R0.jsonl> --r0k <t3_k1/las_T3_R0K.jsonl> --t3 <t3_k1/las_T3.jsonl> --dg3-r0 off=<R-0 dg3 출력> --dg3-r0 v4_on=<…> --dg3-t3 off=<T-3b off 출력> --dg3-t3 v4_on=<…> --d1 <v5/d1.jsonl>`. 실행할 때마다 436.8 sha와 rev5 1 #5의 봉인 11개(원판, rev1~rev4c, rev3 키 목록, rev5, R-0K 키 목록 — R-0K 목록 sha는 `las_targeted_rules_rev5.sha256` 둘째 줄)를 확인한다. 어긋나면 종료 2(S-1·H-T3-0). R-0K 목록은 정렬 키 + LF의 sha256 `9399c492…`(rev5 2.3)도 다시 계산한다.
- 종료 코드(rev3·rev5): 0 통과, 1 기준 실패(H-T3-1K, H-T3-5), 2 판정 없는 멈춤(H-T3-0·3·2·1·1Q·4·6) 또는 규칙 sha 불일치, 3 도구 오류. 멈춤은 rev5 4절 순서로 정렬해 `stop_order`에 적고 첫 멈춤으로 종료 코드를 정한다. 436.8 등급 `status_4368`이 `통과`가 아니면 S-14다.
- dg3 출력 형식은 아직 없어서 jsonl 줄 또는 `results[]`·`records[]` JSON을 받는다. 키는 `key`(또는 `cand=` 접두가 없으면 `cand=<cand>#<key>`), 해시는 `commands_sha256`(`r79.commands_sha256` 포함), 사건은 `event_names` 또는 `events`. 폴더(off·v4_on)는 CLI `FOLDER=`로 준다(확인 필요 T3-a).

| 규칙 | 경로 2 |
|---|---|
| "작동"(rev3 3) | 줄 사건에 `INFO_LIFTOFF_SLOW`(이름의 ':' 앞 부분이 정확히 같음, `_END` 제외)가 1개 이상. `event_names` 개수, 없으면 `events` |
| `would_block_any`(rev5 2.1) | `resume_k1`(또는 `controller_meta`) `slope_clearance_margin.order_gate.decisions[*].would_block` 중 참이 있음. 없으면 결측 |
| R-0 K-2(rev3) | D-1 5키 + dg3 2기록: 해시 = 기준(D-1은 `--d1` 줄, 없으면 키 목록), 태그 V0 없음·VB `final_C4G2_P3`, 작동 0. 실패 H-T3-1, 키·태그 H-T3-3 |
| R-0K K-1K·K-2K(rev5 3.2) | 키 = R-0K 45, 태그 `final_C4G2_K1`/`_P3_K1`, LAS-b 끔, 관문 켬, 작동 0(H-T3-3). (ii) `would_block_any` 거짓 → 해시 = 저장, (iii) `r0_no_r4` 거짓·해시 같음(H-T3-1K). (iv) `uniform_r4` 막힘 → H-T3-1Q. `patch_r4`는 기록 |
| T-3K K-1·K-3 | 키 = T-3a 228 + T-3c 76(+ T-3b 4), 태그 `final_C4G2_LAS_K1`/`_P3_LAS_K1`, `_LAS`만 또는 `_FB`면 H-T3-3. 설정: LAS-b 9값 = b0(프리셋), 관문 켬, `slope_clearance_margin.enable` 참, `flat_soil_margin_m` 0.03 |
| $B(k)$(rev5 3.1) | R-0K 키는 R-0K 줄(해시·`d1` 블록), 그 밖은 `--d1` 저장 줄(없으면 rev3 키 목록, G6-2는 rev4a 1에 따라 키 목록 값을 쓰지 않음), dg3는 키 목록 `shadow_commands_sha256_all_folders` |
| rev4a 1 대조 | `--d1`이 있으면 키 목록의 해시·verdict·fail_items·P3-2·READY·행정·FAULT 이름을 저장 줄과 대조, 다르면 H-T3-3 |
| K-4 | T-3a 바탕 G1 72 + T-3b 4: 작동 → H-T3-4, 미작동·해시 다름 → H-T3-5(rev4a 3) |
| K-5 | 미작동 줄 해시 = $B(k)$, R-0K 밖 미작동 줄은 `would_block_any` 거짓(G-c). 위반 H-T3-5 |
| K-6a~e | 작동 줄: 기준 pass·allowed_stop → fail 금지, 기준 fail은 `fail_items` 포함 관계 / `P3-2`·`G6-2_loc` 기준 참 → 새 값 참(없음 = 위반, 기준에 항목 없으면 해당 없음) / FAULT 접두 이름 ⊆ 기준(`event_names` 없으면 위반) / READY 증가 ≤ 5 s(기준 수·새 None 위반, 둘 다 None 통과) / 행정 증가 ≤ 0.001 m(어느 쪽이든 None 위반). 위반 H-T3-6. 비교 허용은 436.8 7.6의 1e-9 |
| K-7(rev3, rev5 3.4) | 작동 줄 기록: `would_block_any`, `applied` 수, 첫 결정 dP = n_P − n_S, 기준선 출처, 기준선 줄과 막힘 결정 집합이 다른지, LAS-b 블록 |
| 하지 않는 것 | K-0 정체성(커밋·도구·c2.py sha·스레드는 줄 밖 `.identity.json`·헤더에 있음), H-T3-0의 작업 트리·래퍼·출력 파일 존재·dg3 T4h 메타 사전 확인(실행 전 관문) |

- 동작 확인(판정 아님): T-3 결과가 아직 없어 봉인 키 목록으로 만든 합성 줄을 저장 `v5/d1.jsonl`과 함께 돌렸다. rev4a 1 대조 304키 차이 0, 멈춤 0.
- 시험 `test_p2_t3k.py`(12개): 키 목록 수, 전부 통과, H-T3-1, H-T3-1K·1Q, 태그 `_LAS`만·LAS-b 값 H-T3-3, G1 작동 H-T3-4·미작동 해시 H-T3-5, K-6 통과·READY·행정·FAULT 위반, K-6a·b 집합·항목, dg3 작동·키 수, 오류 줄 H-T3-2, R-0K 밖 막힘 H-T3-5, 실제 봉인 11개 sha.

## rev3 반영 (436.8 `v5_resume_4368_rules_rev3.md`, sha256 `dad8dfa6…`, 2026-11-13)

다섯 도구 모두 rev3 sha를 원판·rev1·rev2와 함께 확인한다(`p2_4368.check_seals`). 앞 절의 정의와 다른 곳은 아래가 맞다.

| 절 | 도구 | 반영 |
|---|---|---|
| R3-F1·F2·F3 | `p2_4368.py` | 이미 맞음: S-15는 묶음별 줄 수만, G1 단독 바탕 = 균일 계열, t_D 입력 `scm_crawler_normal_N` |
| R3-F4 | `p2_4368.py anchors` | 부록 B 데이터 파일도 CRLF → LF 정규화 sha가 기록과 같으면 통과, 기록에 두 sha와 "CRLF 변환만 다름" |
| R3-A1 | `p2_d1.py` | G-3 예외 = `job.d1.tags`에 `ASSUMED_BOUNDARY`가 있는 실행 전부(VB·V0, 모든 ε·오거). 예외 줄은 "가정 경계 미성립"으로 적고 사용자 질문. 태그와 (H-S-0, fup-rec)가 다른 행은 기록 |
| R3-A2 | `p2_d1.py` | 세 층: ① H-R 다섯 항목 재판정(앞 절 교차 확인) ② `d1.items`·`fail_items`로 `d1.verdict` 재집계: 허용 행(H-R-A·H-S-0·H-S-1·H-S-A)의 `harness_class` = `stroke_limited_stop`이면 `allowed_stop`(실패 항목은 기록), 아니면 `fail_items`가 있으면 `fail`, 없으면 `pass`. 거짓 항목이 `fail_items`에 없으면 강등 기록(이름에 "demot")이 있어야 함 ③ 선별. ①·②가 기록과 다르면 그 줄은 판정 불가(S-13). 저장 `d1.jsonl` 868줄에 ②를 돌리면 차이 0 |
| R3-A3 | `p2_d1.py` | t_READY = `values.times.t_first_ready_s`. 줄의 단계 기록에서 첫 단계 시작 ≤ 0.1 s여야 하고, `d1.t_ready_s`와 1e-9 안에서 같아야 함. 단계 기록이 없으면 판정 불가. 저장 `d1.jsonl`에는 단계 기록 필드가 없음(확인 필요 R3-A3) |
| R3-B1·B6·B7 | `p2_u3.py` | 정착 v2 재계산(398.3: pen_mean = pen_inst + (y Δφ − x Δθ), Δ는 deg → rad, 좌표 m → mm, \|pen_mean + gap\| ≤ 1 mm, 자세 허용 max(0.005°, 잔차 + 0.002°)). 대상 slope·h6·h9·연구 B·D와 D-1 재사용 줄(`u3.settle_v2`). `result`와 K-10 대조, `tolerances`가 다르면 S-11, `table_sha256` 대조. `settle_check_fail`은 재계산 `ok` 거짓일 때만 실패, 아니면 판정 불가. `no_table_check`는 해당 없음으로 셈. 연구 D 시작 틈 패드는 `gap_target_source` = `start_gap` 목표, 표 목표로도 계산해 `ok`가 달라지는 줄 수를 기록 |
| R3-B2 | `p2_u3.py` | 연구 B·C·D는 입력 키 파일(`s9/rev85/finB2_x426b.json` 84, `fin_x426_C.json` 패드 B 34, `fin_x426_D.json` 33)의 키 집합과 같은 출력 파일 하나로 셈 |
| R3-B3 | `p2_u3.py` | 재사용 = 최상위 `reuse` = `"d1"`, `d1_key`가 H-1 줄의 `d1.key` 하나와 맞아야 함, `meta.v5.reuse_d1.<suite>.reused` 수와 같아야 함 |
| R3-B5 | `p2_u3.py` | IND_LAS 관문 = 사건 이름이 `INFO_LIFTOFF_SLOW:`로 시작(`_END` 제외). 관문이 서지 않은 사례의 해시가 IND와 다르면 어댑터 결함, 사건 목록 없으면 "기록 불완전" |
| R3-C1~C8 | `p2_v5j.py` | H-5 등급 = η_v 0.85 T1 + H0, 0.80 T1·T3·T4·분류는 기록(분류 C면 v5 종합 문장 전에 묻기). J1 pass ↔ `stroke_limited_stop`은 기록(S8 예외). 사양 미달 표시 F_min + 5 kN. J3 경사는 줄의 바닥 각(없으면 FLAG 한계 미정 기록). J7 이름 = 수치 구획을 뺀 나머지. J11 대체 다리 줄의 `n_late` None = 판정 불가. J-P3 로드 판독 = T4h, 없으면 구성(사건 경로 = 있음, steady 사례 = 없음, 그 밖 판정 불가), 선언 = 필드, 없으면 steady 사례 구성 |
| R3-D1~D4 | `p2_t3k.py` | dg3 키는 `cand=current#` 유무 같은 키, 폴더는 기록된 `two_pressure.extend_start_rule`(`tracked_bound` = v4_on)로 정함, CLI 폴더와 다르면 H-T3-3. R-0 V0 태그는 키 없음·null만. K-0은 세 출력 옆 `.identity.json`의 커밋·도구·c2·스레드 필드 대조(다르면 H-T3-3, 없으면 판정 불가). H-T3-0 사전 검사는 두 경로 대상 아님. 비교 허용 1e-9 |

## rev4 반영 (`v5_resume_4368_rules_rev4.md`, sha256 `7ea87a30…`, R4-C)

rev3 절과 다른 곳은 아래가 맞다. 다섯 도구 모두 rev4 sha도 확인한다.

| 절 | 도구 | 반영 |
|---|---|---|
| R4-C1 | `p2_d1.py` | 원점은 F-1 `values.times.t_check_start_s` ≤ 0.1 s(+1e-9). 필드가 없으면 "정의에 의함"(폐루프 시작 = 0, 첫 주기 T_s)으로 적고 판정 불가로 두지 않는다. `d1.t_ready_s` 대조는 그대로. 출력 `R3-A3.origin_basis`에 근거별 줄 수. 저장 `d1.jsonl`은 868줄 모두 정의에 의함, READY 판정 불가 0 |
| R4-C3 | `p2_d1.py` | 강등은 F-2 `d1.demoted_items`(`item`·`rule` ∈ {377, 424.11.2, 424.8.1, 419.8}·`flag`)의 `item` 집합 = "거짓 항목 − `fail_items`". 다르거나 필드가 없으면 판정 불가(S-13). 이름 "demot" 추정은 지웠다. 저장 `d1.jsonl`(F-2 없음)은 868줄 모두 판정 불가가 기대값 |
| R4-C2 | `p2_u3.py` | 단위 deg → rad, m → mm(앞 절 그대로). `tolerances` 세 값이 398.3과 1e-9 안에서 같지 않으면 S-11. 표 목표 패드는 `gap_target_mm` = F-5 `settle_v2.inputs.table_gap_target_mm`, 필드가 없으면 판정 불가. 연구 D의 표 목표 재계산도 이 필드 |
| R4-C4 | `p2_t3k.py` | K-0 = `.identity.json`의 `start`·`end`: `head` 같음(+ `--git-at-start`), `is_clean` 또는 `status_porcelain`의 파일이 `--allowed-dirty` 안, `code_diff_sha256`·`tools_sha256`·`c2_sha256` start = end(c2는 `git show <git_at_start>:03_src/outrigger_sim/control/c2.py` sha와도), `start.env` 스레드 네 개 = 1·`MKL_THREADING_LAYER` = TBB, `OUTRIGGER_LOC_SHADOW` 없음. 세 출력 값이 다르면 H-T3-3, 필드가 없으면 판정 불가 |
| R4-C5 | `p2_v5j.py` | J3 바닥 각 = F-3 `values.case_floor_deg`([roll, pitch]), D-1 줄은 `job.d1` 각. 없으면 경사 판별 "판정 불가", FLAG 한계 "미정"(기록, 등급 영향 없음) |

## rev5·rev6 반영 (`rev5` sha256 `452a8436…`, `rev6` `809e5639…`)

| 절 | 도구 | 반영 |
|---|---|---|
| R5-D1, R6-C3 | `p2_d1.py` | `G6-7_preloc` 거짓 줄: F-8 `d1.g6_preloc.preloc_starts`의 참 최소 ≥ F_min ∧ FAULT 0(`values.events.fault_events`)으로 `preloc_flag_ok`를 다시 계산해 기록과 대조(다르면 판정 불가). 참 → `demoted_items`에 (G6-7_preloc, 377, `P3-8_demoted`), 거짓 ∧ G6-3 참 ∧ FAULT 0 → (G6-7_preloc, `U-S9-G6c`, `P3-8_preloc_loss`), 그 밖 → G6-7은 `fail_items`에 있어야 함. `preloc_flag_ok`·시작 기록이 없으면 판정 불가. 시작 기록의 참 최소 키는 `true_min_N`(대체 `F_true_min_N`·`min_true_N`·`true_min_kN`, 확인 필요) |
| R5-B3 | `p2_v5j.py` | LS 행의 J11 대체 다리 n_late > 0 = `L-e` 멈춤(VB는 H-7) |
| R6-C2 | `p2_t3k.py` | K-0: `.identity.json` `start`·`end`의 `git.head`(같음, `--git-at-start`), `git.is_clean` / `git.status_porcelain`(`--allowed-dirty`), `threads` 다섯(넷 = 1, TBB), `rules_seals` 모두 ok. 제어기·도구 sha는 출력 줄·헤더 정체성(`git_head`·`c2_sha256`·도구 `sha256`·스레드·작업자·affinity, 최상위 또는 `identity` 블록)이 모든 줄에서 같고 세 출력이 서로 같아야 함. `OUTRIGGER_LOC_SHADOW`는 `--steps` 단계 파일에 그 이름이 없어야 함(없으면 판정 불가). R4-C4 대응은 이것으로 바뀜 |
| 공통 | `p2_4368.py` | rev5·rev6 sha 확인 추가 |
| 범위 밖 | – | R6-C1 SA-4(F-9), R5-C3 seedext 짝, R5-D3 F-4는 H-6~H-10 몫이라 이 도구들에 없음 |

## rev7 반영 (`v5_resume_4368_rules_rev7.md`, sha256 `e81f7d31…`, 2026-11-13)

앞 절과 다른 곳은 아래가 맞다. 기록 필드 이름·단위·형식은 rev7 R7-3 대응표만 근거로 쓴다(경로 1 코드·출력은 열지 않았다).

| 절 | 도구 | 반영 |
|---|---|---|
| R7-7 봉인 확인 | `p2_4368.py`(`check_seals`, 다섯 도구 공통) | rev7 raw sha·`.sha256` 첫 값·LF·BOM 없음을 원판~rev6과 같이 확인. 출력 `seals.rev7_sha256` |
| R7-3a F-8 | `p2_d1.py` | `d1.g6_preloc`을 표의 이름으로만 읽는다: `preloc_flag_ok`(bool 또는 null), `preloc_starts[]`의 `t_s`(0.01 s)·`leg`(FL·FR·RL·RR)·`true_min_kN`(kN, 0.01 kN, null 가능, 사건 순서), `source` 고정 문자열. 예전 대체 이름(`true_min_N`·`F_true_min_N`·`min_true_N`)은 읽지 않는다. 표와 다르면 **S-11 멈춤(종료 2)**이고, F-8 기록이 있는 모든 줄(G6-7 참인 줄 포함)에서 본다(출력 `R7-3a_g6_preloc_format`). `preloc_flag_ok` 재계산 = 시작 ≥ 1개 ∧ 모든 `true_min_kN` ≠ null ∧ 기록값(0.01 kN) ≥ 9.414589 kN(허용 1e-9 kN) ∧ 실행 `final_phase` ∉ {fault, fault_reground}. 시작이 없으면 거짓. null(r72 키 없음)은 판정 불가(R6-C3 3). 분기 2의 "FAULT 없음"은 앞 판대로 `values.events.fault_events` = 0 |
| R7-3b T-3K 정체성 | `p2_t3k.py` | 첫 줄 `header.identity`, 다음 줄부터 `t3.identity`(`git_head` 40자리, `sha256` = 파일 6개 → 64자리, `c2_sha256` 64자리, `threads` 키 5개 → 문자열 또는 null, `workers` int, `affinity` 문자열 또는 null)와 `t3.commit`·`t3.workers`·`t3.affinity_hex`가 같은 값인지 본다. 형식·이름이 다르거나 첫 줄이 헤더가 아니면 **S-11**. 예전 이름(`tool_sha256`, `affinity_mask`, 최상위 `identity`)은 읽지 않는다. 헤더와 모든 줄, 세 출력의 같음(R6-C2)은 그대로 H-T3-3. 재집계에서는 헤더 줄을 건너뛴다 |
| R7-1c R-0 태그 | `p2_t3k.py` | 키 있음·판 확인용 읽기(`read_tag`): 기록 태그가 있으면 그 값, 없거나 null이고 `t3.las` = `t3.gate` = `"off"`면 `final_C4G2`(출력 `R7-1c_tag_reading`, 줄마다 `tag_read`·`tag_read_source`). 그 밖에 태그가 없으면 **S-11**. K-2(R-0 V0 기대 "없음")와 H-T3-3은 바꾸지 않았다(R3-D2대로 기록 키로 대조, 키에 `final_C4G2`가 있으면 H-T3-3) |
| 멈춤 순서 | `p2_t3k.py` | S-11을 H-T3-0 다음에 둔다(종료 2) |
| R7-4 Chrono 조건부 결측 | `p2_4368.py chrono --gs` | SCM level 행 키 있음 확인에 rev7 표 9개(`GS_CONDITIONAL_R74`)를 쓴다. 결측 허용 조건이 성립할 때만 `conditional_absent`, 아니면 `result_missing`(S-11). `p3b.P3-3_leg_force.F_min_after_N`·`F_min_transient_N`은 `p3b.departure.departed`가 False일 때만, `c2_setup.las_off`는 켬 팔(`r4368.arm` ≠ `"off"`), LAS-b 6개(`start_s`·`end_s`·`end_reason`·`active_periods`·`ramp`·`ramp.periods_applied`)는 끔 팔에서만 허용. 표의 키는 값이 null이어도 있음으로 센다. 표에 없는 `p3b.P3-3_leg_force.t_min_after_s`는 경로 2 키 목록에서 뺐다(경로 2가 읽지 않는 키이고, 언제나 필수로 두면 이탈 없는 행을 멈추고, 조건을 붙이면 규칙에 없는 조건을 만든다). 이 표는 rev7 본문에서 옮겼고 manifest(`chrono_rows_manifest.json`)는 열지 않았다. 그래서 `table_sha256` `eef5129f…`는 다시 계산하지 않는다 |
| R7-6 풀 마스크 | `p2_4368.py chrono` | SCM 행 `identity`에 `placement.affinity_mask_process`·`affinity_mask_ok`와 행 `placement_applied`를 기록한다. `affinity_mask_ok` 거짓은 `records`에 남긴다(판정서 기재, 멈춤 아님) |
| 해당 없음 | – | R7-2 첫 DONE: H-0~H-5 도구는 첫 DONE이나 419.8 조건 5를 다시 계산하지 않는다(`p2_u3.py`는 기록된 `late_loc_reapproach.is_flag`만 읽음). R7-1a·R7-1b(r79·격자 최상위 태그 대조)와 R7-5(경로 1 집계 v2)는 경로 1 도구 몫이다. `p2_4368.py harness`의 태그 읽기는 이미 최상위 `controller_tag`를 먼저 본다 |

### 도구 sha256 (rev7 판, LF 바이트)

- 이 표는 rev7 판 당시의 이력 값이다. **현재 값은 rev12 표**("rev12 반영" 절 "도구 sha256 (rev12 판)")에 있다.

| 파일 | sha256 | 이 판에서 |
|---|---|---|
| `p2_4368.py` | `e033ca4ba988252ba2181a3ca398c725ebe19ff84fed3dbd1b60cb7301026a0a` | 바뀜 |
| `p2_d1.py` | `6d18f6dbfa891ea8faf2eec45cb26c023a045aa0170b7cfac4b1c0aa28cde24d` | 바뀜 |
| `p2_t3k.py` | `f4a84aba0beb07fe2de09fa6edd803406baefee73fdd90f8957a9dd258a6777a` | 바뀜 |
| `p2_u3.py` | `408944c498da8736e343c2dbc2d816f6fdbe8a5ecd73a0a96689f06680bc5f28` | 그대로(rev7 봉인 확인은 `p2_4368.check_seals`로) |
| `p2_v5j.py` | `5772624cb28e414ceeb38af3eb6d386a2e0a78857db8a5ea9a5d3cd2ec5f7d8b` | 그대로(같음) |
| `test_p2_4368.py` | `0b6899df8b25f5a105bf0f0c25b336077c62abb4960dfee972e6eaa05f9bfa3f` | 바뀜(49개) |
| `test_p2_d1.py` | `d1b61db2979ea1658eda4f515936e407a2d52666efeff9575c583dcecd0778ce` | 바뀜(17개) |
| `test_p2_t3k.py` | `c3696fb7cfc1bc240f71b14b5c06e7b5b2a18f3cdf7b3c3a6f47f5ea57b933be` | 바뀜(19개) |
| `test_p2_u3.py` | `245c03ff2a731fb33606f992328660f46f669dbee41cac4e20dc58b01133bb99` | 그대로(11개) |
| `test_p2_v5j.py` | `d52ca6adb89f77f6bd952bf6ff03f966f9cd7d0a05486af7e044ee700fb0a418` | 그대로(16개) |

- 자체 시험은 다섯 파일 112개(앞 판 103개)다. pytest 개수는 매개변수화한 시험을 하나씩 센다.
- `p2_4368.py`가 바뀌었으므로 이 파일을 sha로 import하는 `../path2_v5c/p2v5c_common.py`(`P2_CORE_SHA` `dc631509…`)는 새 sha로 고칠 때까지 `P2-SHA`(종료 2)로 멈춘다. 그 폴더는 이 도구 작성자 소유가 아니라 고치지 않았다. (이력: 현재 값은 rev10 절의 도구 sha 표와 `path2_v5c`의 `P2_CORE_SHA`가 맞다)

## rev8 반영 (`v5_resume_4368_rules_rev8.md`, sha256 `3ecafaaf…`, 2026-11-13)

앞 절과 다른 곳은 아래가 맞다. 근거는 원판~rev8 문장과 R8-3a 이름표뿐이다(경로 1 코드·출력은 열지 않았다).

| 절 | 도구 | 반영 |
|---|---|---|
| R8-4 봉인 확인 | `p2_4368.py`(`check_seals`, 다섯 도구 공통) | rev8 raw sha가 코드의 봉인 sha와 `.sha256` 첫 값 둘 다와 같고 LF·BOM 없음일 때만 통과(아니면 S-1, 종료 2). 출력 `seals.rev8_sha256` |
| R8-3·R8-3a G-S | `p2_4368.py chrono --gs` | SCM `run_S9.py level` 행(열린 루프 제외)마다 `<행>/step_series.npz` `law_locked`를 본다: 파일·키 있음, int8, [N, 4], 값 ⊂ {−1, 0, 1}, 같은 파일 `t_s`와 행 수 같음, `t_s` 간격 1 ms(경로 2 허용 1e-6 s). 하나라도 어긋나면 **S-11**. 행 `gs_law_locked`, 출력 `R8-3_law_locked_check`(행 수, `missing`, `problems`). 다리별 0→1·1→0 수는 기록만(−1은 잠김으로 셈, 개정 6 6절) |
| R8-3 본 실행 | `p2_4368.py chrono` | 같은 형식 검사를 행 `law_locked`에 기록. C-5 행에서 어긋나면 **판정 불가**(J11 판정 불가 → 대체 다리 $n_{late}$ 멈춤을 확인할 수 없으니 묶음을 멈추고 묻는다, 종료 1). C-5 밖 행은 기록만. J11 값 자체는 이 도구가 계산하지 않는다(C-5 경로 2 `../path2_chrono` 몫) |
| R8-2 태그 | `p2_4368.py chrono` | Chrono 행의 태그 = argv `--expect-controller` 값 + `expect_controller` 확인 참(원판 6절, RV1-10 a). 기록 태그(`controller_tag`·`v5_hydraulics.controller_tag`)는 있으면 같아야 하고(다르면 S-2), `v5_hydraulics` 블록이 없는 SCM 행(V0·S6SEED)에서는 없어도 멈추지 않는다(기록). L2b·L1-R 행은 기록 태그가 없으면 앞 판대로 S-2. G-S 키 목록에서도 `v5_hydraulics.controller_tag`는 그 블록이 있는 SCM 행에서만 요구한다(앞 판에서는 V0·S6SEED 행에 S-11이 났다) |
| R8-2 ③ 대조·J-P3 범위 | `p2_4368.py chrono` | ③ = `is_extend_start_tag(태그)`. argv `--extend-start-tracked` 유무, `v5_hydraulics` 블록이 있으면 `hydraulic_options.extend_start_tracked`(키 없음 = 끔)가 ③과 다르면 **S-2**. ③ 행: `controller_meta.two_pressure.settings.extend_start_rule` = `tracked_bound`가 아니면 S-2, 키가 없으면 기록 "J-P3 판정 불가"(J-P3 등급은 C-5 경로 2 몫). ③ 아닌 행: J-P3 해당 없음, 키 없음을 결측으로 세지 않음. 행 `jp3_scope`, 출력 `R8-2_jp3_scope`(상태별 수) |
| R8-1b 이름 | `p2_4368.py harness` | H-6·H-7 줄의 `controller_settings["two_pressure.extend_start_rule"]`(점이 든 키 하나)를 그대로 읽는다. 앞 판은 이 키를 중첩 경로로 찾아 언제나 "not in line" 기록만 남기고 ③ 대조를 건너뛰었다 |
| 바꾸지 않음 | – | R8-1 재계산 대조(T4h 없는 r79·격자 job)는 R8-1d가 경로 1 도구(`resume4368_judge`) 몫으로 정했다. `p2_4368.py harness`는 앞 판대로 기록 태그를 kind 기대 태그와 대조한다. `p2_v5j.py` J-P3은 이미 ③을 `is_extend_start_tag`로만 정하고 ③ 아닌 줄을 `not_applicable_tag`로 둔다(R8-2와 같음). L2b `pads.npz` `law_locked` 읽기(R8-3a 둘째 줄)는 C-5 J11 계산이라 `../path2_chrono` 몫이다. `p2_d1.py`·`p2_t3k.py`·`p2_u3.py`에 rev8이 요구하는 것은 없다(봉인 확인은 공통 함수로 들어감) |

- 2026-11-13 G-S `…_082117`에 이 판을 돌린 결과(참고, 11.2 충족에 쓰지 않음, R8-4): SCM level 9행 모두 `law_locked key absent`로 S-11(R8-4가 예상한 결과), 그 밖 S-11 없음.

### 도구 sha256 (rev8 판, LF 바이트)

- 이 표는 rev8 판 당시의 이력 값이다. **현재 값은 rev12 표**("rev12 반영" 절 "도구 sha256 (rev12 판)")에 있다.

| 파일 | sha256 | 이 판에서 |
|---|---|---|
| `p2_4368.py` | `bebed9f1663ce17a0ea24c72de67080b335109dfb83d735971fe68cff4ed9d31` | 바뀜 |
| `p2_d1.py` | `6d18f6dbfa891ea8faf2eec45cb26c023a045aa0170b7cfac4b1c0aa28cde24d` | 그대로 |
| `p2_t3k.py` | `f4a84aba0beb07fe2de09fa6edd803406baefee73fdd90f8957a9dd258a6777a` | 그대로 |
| `p2_u3.py` | `408944c498da8736e343c2dbc2d816f6fdbe8a5ecd73a0a96689f06680bc5f28` | 그대로 |
| `p2_v5j.py` | `5772624cb28e414ceeb38af3eb6d386a2e0a78857db8a5ea9a5d3cd2ec5f7d8b` | 그대로 |
| `test_p2_4368.py` | `2b887bc23ab0ac37b3684ae13fc474c5efbd8776d6e2e7570b77b79ecb9e9fa7` | 바뀜(65개) |
| `test_p2_d1.py` | `d1b61db2979ea1658eda4f515936e407a2d52666efeff9575c583dcecd0778ce` | 그대로(17개) |
| `test_p2_t3k.py` | `c3696fb7cfc1bc240f71b14b5c06e7b5b2a18f3cdf7b3c3a6f47f5ea57b933be` | 그대로(19개) |
| `test_p2_u3.py` | `245c03ff2a731fb33606f992328660f46f669dbee41cac4e20dc58b01133bb99` | 그대로(11개) |
| `test_p2_v5j.py` | `d52ca6adb89f77f6bd952bf6ff03f966f9cd7d0a05486af7e044ee700fb0a418` | 그대로(16개) |

- 자체 시험은 다섯 파일 128개(앞 판 112개)다. 더한 것: rev8 봉인 확인과 불일치 S-1, `law_locked` 형식 6가지·정상·1 ms 간격, G-S 모드 3가지, 본 실행 C-5 판정 불가, R8-2 J-P3 범위·요청 기록 대조, `v5_hydraulics` 없는 SCM 행, R8-1b 점 키.
- `p2_4368.py`가 바뀌었으므로 `../path2_v5c/p2v5c_common.py`의 `P2_CORE_SHA`를 `bebed9f1…`로 고쳐야 한다(R8-4, 그 폴더 작성자 몫). `p2_v5j.py`는 바뀌지 않았다. (이력: 현재 값은 rev10 절의 도구 sha 표와 `path2_v5c`의 `P2_CORE_SHA`가 맞다)

## rev9 반영 (`v5_resume_4368_rules_rev9.md`, sha256 `4cf7843c…`, 2026-11-13)

앞 절과 다른 곳은 아래가 맞다. 근거는 원판~rev9 문장뿐이다(경로 1 코드·출력은 열지 않았다). rev9 R9-4가 판별 입력으로 정한 `chrono_rows_manifest.json`은 이 판에서 도구 입력으로 읽는다(아래 독립성 공개).

| rev9 | 도구 | 반영 |
|---|---|---|
| R9-8 봉인 확인 | `p2_4368.py`(`check_seals`, 다섯 도구 공통) | rev9 raw sha가 코드의 봉인 sha와 `.sha256` 첫 값 둘 다와 같고 LF·BOM 없음일 때만 통과(아니면 S-1, 종료 2). `.sha256`이 없어도 S-1. 출력 `seals.rev9_sha256` |
| R9-1 태그 확인 | `p2_4368.py chrono` | Chrono 제어기 행(SCM·L2b·L1-R, 열린 루프 제외)의 `expect_controller.ok`(L2b·L1-R) 또는 `c2_setup.expect_controller.ok`(SCM)가 참이 아니거나 키가 없으면 **S-2**. `--gs`에서는 **S-2와 S-11**을 함께 낸다(앞 판 G-S는 키 있음만 봐서 값 거짓을 놓쳤다). 본 실행은 앞 판대로 S-2이고, J-P3만 판정 불가로 두고 계속하지 않는다. 행 `r91_expect_controller_ok`, 출력 `R9-1_expect_controller`(본 행 수, S-2 수) |
| R9-2 형식 검사 | `p2_4368.py chrono`(`law_locked_format`) | 두 엔진 같게: SCM `run_S9.py level` 행 `<행>/step_series.npz`(시간 열 `t_s`), L2b `run_S8C.py` 행 `<행>/pads.npz`(시간 열 `t`). 항목 1 시간 열 있음(1차원), 2 [N, 4]이고 N = 시간 열 길이, 3 int8, 4 값 ⊂ {−1, 0, 1}, 5 인접 간격 \|Δt − 1 ms\| ≤ 10⁻⁶ s(절차 값), 6 −1 꼴(R9-3). 행 `failed_items`(`1_time_column`~`6_minus1`), `max_abs_dt_error_s`. 앞 판은 L2b `pads.npz`를 보지 않았다(C-5 J11 계산 쪽 몫으로 뒀음). rev9 R9-2 "두 엔진에 같게 쓴다"와 R9-5로 이 도구도 본다 |
| R9-3 −1 꼴 | `p2_4368.py`(`minus1_pattern`) | `none`(−1 없음), `pre_arming`(처음부터 이어지는 −1이고 네 다리가 같은 표본에서 함께 벗어남, 그 뒤 −1 없음 → 잠김, 통과), 형식 오류 `whole_run`(모든 표본·다리 −1), `after_arming`(그 다리에 0 또는 1이 나온 뒤의 −1, 네 다리가 함께 −1로 돌아가는 경우 포함), `leg_mismatch`(다리마다 벗어나는 표본이 다름, 끝까지 −1인 다리 포함). 행 `minus1_patterns`, `pre_arming_samples`. 다리별 0→1·1→0 수(−1 = 잠김)는 형식이 맞을 때만 기록 |
| R9-5 결측·형식 오류 | `p2_4368.py chrono` | `--gs`: SCM level·L2b 행 모두 키 없음·형식 오류 = **S-11**(행 종류 무관, R9-6 "G-S 키 확인은 그대로"). 본 실행 C-5 행(두 엔진): **판정 불가**(J11 판정 불가 → 대체 다리 $n_{late}$ > 0 멈춤을 확인할 수 없어 묶음을 멈추고 묻는다, 종료 1). 행 `law_locked.handling` = `c5_not_judgeable_stop` |
| R9-6 J11 범위 | `p2_4368.py chrono` | C-5 밖 행(C-1~C-4, C-8, J_P)의 결측·형식 오류는 멈춤·판정 불가가 아니라 "입력 없음" 기록(`handling` = `input_missing_recorded`)과 수. J11 값 자체는 이 도구가 계산하지 않는다 |
| R9-4 LS 행 | `p2_4368.py chrono --rows-manifest <chrono_rows_manifest.json>` | 행마다 manifest `batches.<묶음>.rows[]`(묶음 = 배치 폴더 `batch_<묶음>_<날짜>_<시각>`, 같은 `case`)의 `v5_setting`과 `batch.json` `cases[].v5_setting`을 맞춰 본다. 같고 LS1~LS4 = `ls`, 같고 다른 값 또는 둘 다 없음·None = `not_ls`, 한쪽만·다름·manifest 행 둘 이상 = `undecidable`. 행 이름은 읽지 않는다. `ls`인데 태그가 ③ 켬이 아니면 **S-2**. C-5 행의 `undecidable`은 기록("LS 판별 불가", 그 행에서 대체 다리 $n_{late}$ > 0이면 멈춤 — J11 계산 쪽에서 판정). 옵션을 주지 않으면 `not_checked`로 기록. 출력 `R9-4_ls_rows`(분류별 수, LS 행, 판별 불가 행, C-5 판별 불가 행). 기대 태그 계산(`expected_chrono_tag`)도 LS를 LS1~LS4 정확 일치로 바꿨고, LS 끔 팔은 ③ 끔 팔 태그(`final_C4G2_P3_K1`)를 기대한다(앞 판은 `startswith("LS")`, 끔 팔에서는 VB만 ③으로 봤다) |
| R9-8 G-S 기록 | `p2_4368.py chrono --gs` | 출력 `R9-2_law_locked_check`: 행 수, 엔진별(행·통과·결측·형식 오류), 결측 수, 항목별 어긋난 수, −1 꼴별 수, C-5 판정 불가 수, C-5 밖 입력 없음 수, 최대 간격 오차. 앞 판 `R8-3_law_locked_check`(행·`missing`·`problems`)도 그대로 낸다(이제 L2b 행 포함) |
| 바꾸지 않음 | – | R9-7(K1 단독 태그·규칙 5)은 R8-1 재계산 대조에 쓰이는데, 그 대조는 R8-1d·R8-4대로 경로 1 도구 몫이라 이 폴더에 해당 코드가 없다. 하네스 태그 상수 `TAG_C4OFF_V0` = `final_C4G2_K1`, `TAG_C4OFF_VB` = `final_C4G2_P3_K1`은 R9-7과 이미 같다. `p2_v5j.py`의 J11(L-e/H-7)은 하네스 줄 `job.setting`으로 가르는 하네스 J 항목이다. R9-4는 Chrono 행의 정의이고 행 이름 토큰도 쓰지 않으므로 바꾸지 않았다. C-5 Chrono 행의 J11 계산(`../path2_chrono/p2_kinds.py`의 `"_LS" in row.case` 판별과 −1 읽기)은 이 폴더 밖이라 고치지 않았다(그 폴더 작성자 몫). `p2_d1.py`·`p2_t3k.py`·`p2_u3.py`에 rev9가 요구하는 것은 없다(봉인 확인은 공통 함수로 들어감) |

- 2026-11-13 G-S `…_082117`에 이 판을 돌린 결과(참고, 11.2 충족에 쓰지 않음, R9-8): 12행. SCM level 9행 모두 `law_locked key absent`로 S-11(rev8 R8-4가 예상한 결과). L2b 1행(`GS_D1C2_middle_fdown3.2_Fs4`)은 `pads.npz` 통과(−1 없음, 최대 간격 오차 3.32×10⁻¹⁴ s — rev9 R9-2에 적힌 값과 같음). R9-1 S-2 0/11, R9-4 `not_ls` 11·해당 없음(열린 루프) 1. `…_094502`는 `batch.json`이 없어(중단 실행) 읽지 못했다.

### 도구 sha256 (rev9 판, LF 바이트)

- 이 표는 rev9 판 당시의 이력 값이다. **현재 값은 rev12 표**("rev12 반영" 절 "도구 sha256 (rev12 판)")에 있다.

| 파일 | sha256 | 이 판에서 |
|---|---|---|
| `p2_4368.py` | `7d764a80f43db9431f303bb3d0049c2548788c5928a8cf555b1fa86cc9e44322` | 바뀜 |
| `p2_d1.py` | `6d18f6dbfa891ea8faf2eec45cb26c023a045aa0170b7cfac4b1c0aa28cde24d` | 그대로 |
| `p2_t3k.py` | `f4a84aba0beb07fe2de09fa6edd803406baefee73fdd90f8957a9dd258a6777a` | 그대로 |
| `p2_u3.py` | `408944c498da8736e343c2dbc2d816f6fdbe8a5ecd73a0a96689f06680bc5f28` | 그대로 |
| `p2_v5j.py` | `5772624cb28e414ceeb38af3eb6d386a2e0a78857db8a5ea9a5d3cd2ec5f7d8b` | 그대로 |
| `test_p2_4368.py` | `8fff08a6af3d7174331f01bdaa65bc51b84b660fb7582316a0d6577d935b2024` | 바뀜(89개) |
| `test_p2_d1.py` | `d1b61db2979ea1658eda4f515936e407a2d52666efeff9575c583dcecd0778ce` | 그대로(17개) |
| `test_p2_t3k.py` | `c3696fb7cfc1bc240f71b14b5c06e7b5b2a18f3cdf7b3c3a6f47f5ea57b933be` | 그대로(19개) |
| `test_p2_u3.py` | `245c03ff2a731fb33606f992328660f46f669dbee41cac4e20dc58b01133bb99` | 그대로(11개) |
| `test_p2_v5j.py` | `d52ca6adb89f77f6bd952bf6ff03f966f9cd7d0a05486af7e044ee700fb0a418` | 그대로(16개) |

- 자체 시험은 다섯 파일 152개(앞 판 128개)다. 더한 것(24개): rev9 봉인 확인과 불일치·`.sha256` 없음 S-1, −1 꼴 8가지(없음·무장 전·무장 뒤·전 구간·다리별 어긋남·끝까지 −1인 다리·네 다리 함께 다시 −1·두 오류 겹침), L2b `pads.npz` 시간 열 `t`·항목별 오류·10⁻⁶ s 경계, G-S L2b 4가지(통과·키 없음·파일 없음·무장 뒤 −1), G-S `expect_controller.ok` 거짓·없음 × SCM·L2b(S-2 + S-11), 본 실행 ok 거짓 S-2, 본 실행 L2b C-5 판정 불가·C-1 기록, SCM C-5 밖 기록, R9-4 판별 표·이름 토큰 미사용·LS 끔 팔 태그, LS 행 비③ 태그 S-2와 C-5 판별 불가 기록.
- `p2_4368.py`가 바뀌었으므로 `../path2_v5c/p2v5c_common.py`의 `P2_CORE_SHA`를 위 새 sha로 고쳐야 한다(그 폴더 작성자 몫, 고칠 때까지 `P2-SHA` 종료 2). `p2_v5j.py`는 바뀌지 않았다.

## rev10 반영 (`v5_resume_4368_rules_rev10.md`, sha256 `62a0bd8d…`, 2026-11-13)

rev9 절의 R9-4 행 가운데 아래와 다른 곳은 이 절이 맞다. 근거는 rev10 문장뿐이다(경로 1 코드·출력은 열지 않았다).

| rev10 | 도구 | 반영 |
|---|---|---|
| R10-3 봉인 확인 | `p2_4368.py`(`check_seals`, 다섯 도구 공통) | rev10 raw sha가 코드의 봉인 sha와 `.sha256` 첫 값 둘 다와 같고 LF·BOM 없음일 때만 통과(아니면 S-1, 종료 2). 출력 `seals.rev10_sha256` |
| R10-1a 전체 묶음 이름 | `p2_4368.py`(`full_batch_name`) | 이름 = `batch.json` 최상위 `batch` 값(`V5-RESUME-K1-` 접두어 포함 전체 이름). 폴더 이름의 `batch_` 뒤 `_<YYYYmmdd_HHMMSS>` 앞 부분과 대조한다. 키가 없으면 폴더 이름 부분을 쓴다. 키가 있는데 폴더 부분과 다르거나(폴더가 그 꼴이 아닌 경우 포함), 키도 없고 폴더 꼴도 아니거나, 정한 이름이 manifest `batches` 키가 아니면 **묶음 이름 불명**. 원판 4.3의 짧은 묶음 ID(`C5` 등)는 쓰지 않는다. 앞 판은 폴더 이름만 썼다 |
| R10-1b 경우별 처리 | `p2_4368.py`(`r94_ls_row`) | 두 출처(manifest `batches.<이름>.rows[]`, `batch.json` `cases[]`) 모두 같은 `case`가 정확히 1개여야 한다. 경우 `source_case`: `batch_name_unknown`·`manifest_rows_0`·`manifest_rows_many`·`batch_cases_0`·`batch_cases_many` = LS 판별 **판정 불가**. 1개씩 있으면 `both_values_absent`(두 행 모두 `v5_setting` 없음·None) = LS 아님, `one_value_only`·`values_differ` = 판정 불가, `values_equal` = LS1~LS4면 LS, 아니면 LS 아님. 앞 판은 "manifest 행 없음"을 "값 없음"으로 읽어, `batch.json`에도 값이 없으면 LS 아님으로 뒀다(R10-1b 표 둘째 행). C-5 행의 판정 불가는 앞 판대로 기록("LS 판별 불가"와 경우 이름) |
| R10-1b manifest 파일 | `p2_4368.py chrono` | `--rows-manifest`는 이제 기본값이 `<repo>/06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json`이다(앞 판은 생략하면 `not_checked`). 파일이 없거나, JSON으로 읽히지 않거나, `batches` 객체가 없으면 **입력 오류**: 행을 하나도 판정하지 않고 **S-11**(종료 2), 출력 `rows_manifest_error`, `batches_not_judged`. G-S에서도 같다(G-S 실패) |
| R10-2 G-S 확인 | `p2_4368.py chrono --gs` | Chrono 행마다(열린 루프 포함) 전체 묶음 이름이 정해지고 두 출처에 `case`가 1개씩 있는지 본다. 어긋나면 **S-11**(`G-S R10-2: <경우>`). 출력 `R9-4_ls_rows`에 `source_check`(행·통과·실패), `source_cases`(경우별 행 수), `batch_names`(이름별 행 수), `rows_manifest_sha256`을 더했다. 열린 루프 행은 LS 분류만 `not_applicable`이고 출처 확인은 한다 |
| 바꾸지 않음 | – | `p2_v5j.py`(하네스 줄 J 항목, R10 대상 아님), `p2_d1.py`·`p2_t3k.py`·`p2_u3.py`(봉인 확인만 공통 함수로 들어감). C-5 J11 계산의 LS 판별(`../path2_chrono`)은 이 폴더 밖이다 |

- 2026-11-13 저장 G-S 네 건에 이 판을 돌린 결과(참고, 11.2 충족에 쓰지 않음, R10-3): `…_082117` 12행, `…_010654` 2행, `…_012403` 3행, `…_020211` 2행 모두 R10-2 출처 확인 통과(이름 `V5-RESUME-K1-GS`, 두 출처 1행씩). 경우는 `values_equal` 16, `both_values_absent` 3. 그 밖의 S-11은 기록 추가 이전 G-S의 예상된 결측(SCM `law_locked` 없음, `…_012403`의 L2b·L1-R 기록 키 없음)이다.

### 도구 sha256 (rev10 판, LF 바이트)

- 이 표는 rev10 판 당시의 이력 값이다. **현재 값은 rev12 표**("rev12 반영" 절 "도구 sha256 (rev12 판)")에 있다.

| 파일 | sha256 | 이 판에서 |
|---|---|---|
| `p2_4368.py` | `6e297ea371ad8559d656c7c2d4508d4120c72989424baa4aedcaf2f8f7a7bfa0` | 바뀜 |
| `p2_d1.py` | `6d18f6dbfa891ea8faf2eec45cb26c023a045aa0170b7cfac4b1c0aa28cde24d` | 그대로 |
| `p2_t3k.py` | `f4a84aba0beb07fe2de09fa6edd803406baefee73fdd90f8957a9dd258a6777a` | 그대로 |
| `p2_u3.py` | `408944c498da8736e343c2dbc2d816f6fdbe8a5ecd73a0a96689f06680bc5f28` | 그대로 |
| `p2_v5j.py` | `5772624cb28e414ceeb38af3eb6d386a2e0a78857db8a5ea9a5d3cd2ec5f7d8b` | 그대로 |
| `test_p2_4368.py` | `4773b8b86945bd16274c4549a9776b606f3bde19766ce84e06c72d3724860e8e` | 바뀜(105개) |
| `test_p2_d1.py` | `d1b61db2979ea1658eda4f515936e407a2d52666efeff9575c583dcecd0778ce` | 그대로(17개) |
| `test_p2_t3k.py` | `c3696fb7cfc1bc240f71b14b5c06e7b5b2a18f3cdf7b3c3a6f47f5ea57b933be` | 그대로(19개) |
| `test_p2_u3.py` | `245c03ff2a731fb33606f992328660f46f669dbee41cac4e20dc58b01133bb99` | 그대로(11개) |
| `test_p2_v5j.py` | `d52ca6adb89f77f6bd952bf6ff03f966f9cd7d0a05486af7e044ee700fb0a418` | 그대로(16개) |

- 자체 시험은 다섯 파일 168개(앞 판 152개)다. 더한 것(16개): rev10 봉인 확인과 불일치 S-1, 전체 묶음 이름 6가지(키≠폴더, 키 없음 + 폴더 꼴 아님, 키 있음 + 폴더 꼴 아님, manifest에 없는 이름, 키 없음 = 폴더, 짧은 묶음 ID), 행 수 4가지(manifest 0·여럿, `batch.json` 0·여럿), manifest 입력 오류 3가지(없음, JSON 아님, `batches` 없음), G-S 출처 확인(통과, 이름 불일치 S-11, manifest 행 없음 S-11), 본 실행 C-5 출처 불명 기록. rev9 R9-4 판별 시험은 새 입력(두 출처 행 목록)으로 고쳐 썼다.
- `p2_4368.py`가 바뀌었으므로 `../path2_v5c/p2v5c_common.py`의 `P2_CORE_SHA`를 `6e297ea3…`로 고쳐야 한다(그 폴더 작성자 몫). `p2_v5j.py`는 바뀌지 않았다.

## rev11 반영 (`v5_resume_4368_rules_rev11.md`, sha256 `9bac4524…`, 2026-11-13)

앞 절과 다른 곳은 아래가 맞다. 근거는 rev11 문장뿐이다(경로 1 코드·출력은 열지 않았다).

| rev11 | 도구 | 반영 |
|---|---|---|
| R11-7 봉인 확인 | `p2_4368.py`(`check_seals`, 다섯 도구 공통) | rev11 raw sha가 코드의 봉인 sha와 `.sha256` 첫 값 둘 다와 같고 LF·BOM 없음일 때만 통과(아니면 S-1, 종료 2). 출력 `seals.rev11_sha256` |
| R11-1 4.2 기대값 | `p2_t3k.py`(`line_kind`, `r111_record_check`, `r111_line`) | H-0 D-1 줄마다 줄 종류를 `t3.bundle`·`t3.las`·`t3.gate`로 정한다: `R-0`+off+off = R-0, `R-0K`+off+on = R-0K, `T-3a`/`T-3b`/`T-3c`+on+on = T-3K. 셋 가운데 하나라도 없거나 짝이 표와 다르거나, 줄 종류가 입력 파일(`--r0`·`--r0k`·`--t3`)과 다르거나, T-3K 줄의 `t3.bundle`이 키 목록 묶음과 다르면 기록 결함 **S-3**(`--gs`이면 **S-11**). 원판 4.2 대조: LAS-b 켬(T-3K)은 프리셋 9값(+ P0 덧붙임 값 0), 끔(R-0·R-0K)은 `settings.enable` = false만. 관문 켬(R-0K·T-3K)/끔(R-0)은 `k1_order_gate_effective`와 `slope_clearance_margin.settings.flat_soil_margin_order_gate`가 둘 다 true/둘 다 false. 관문 요청은 T-3K = `preset`, R-0·R-0K는 기록만(`gate_request_recorded`). 어긋나면 **S-3**. 멈춤 순서는 H-T3-0 → S-11 → S-3 → H-T3-3 …(S-3 종료 2). 출력 `H-0.R11-1_record_check`(묶음별 줄 종류 수, `kind_defect`, `record_mismatch`, 요청 기록). 앞 판은 R-0 줄에 4.2 대조를 하지 않았고, R-0K·T-3K는 입력 파일 기준 rev5 2.2 대조(`config_check`, H-T3-3)만 했다. 그 대조는 그대로 둔다 |
| R11-2 T4h 찾기 | `p2_v5j.py u9`(`t4h_places`, `rod_reading_lookup`) | VB 줄의 T4h는 그 줄이 든 `--vb` 파일의 관례 폴더(`<stem>_t4h/`, 같은 폴더의 `t4h/`)에서만 찾는다. `--t4h-root`는 어느 `--vb` 파일에도 관례 폴더가 없을 때만 1개 줄 수 있다. 관례 폴더가 있는데 주거나 2개 이상 주면 **입력 오류**: 판정하지 않고 **S-11**, 종료 2(출력 `R11-2_t4h_places.input_error`). 기록된 `t4h_file`이 찾는 곳 전체에서 0개 또는 2개 이상이면 **S-2**. `t4h_file`이 없는 줄은 앞 판대로 구성 선언으로 읽는다(R3-C8). 출력 `H-5.R11-2_t4h_lookup`(상태별 수). 라이브러리 함수 `rod_reading_from_t4h(line, t4h_root)`는 `../path2_v5c`가 이름으로 쓰므로 그대로 두었다 |
| R11-4 커밋 정체성 | `p2_4368.py chrono --git-at-start <커밋>` | 모든 Chrono 행(열린 루프 포함, `--gs`에서도)의 `batch.json` `cases[].code_at_launch.git.head`가 판정서 `git_at_start`와 같아야 한다(40자리 또는 7자리 이상 약칭의 앞부분 일치). 기록이 없거나 다르면 **S-12**. `result.json` `code_state.git_at_start.head`가 있는 행은 그것도 같아야 한다(다르면 S-12, 없으면 기록만). `--git-at-start`를 주지 않으면 판정 불가(확인 안 함). 출력 `R11-4_commit_identity`(행 상태별 수, `code_state` 상태별 수) |
| R11-5 G-S 행 등급 | `p2_4368.py chrono --gs` | 이 도구는 G-S 행에 등급을 내지 않는다(키 있음·형식·정체성만). 출력 `R11-5_gs_grades`에 "G-S 행 등급은 판정하지 않음"을 적는다 |
| 바꾸지 않음 | – | R11-3(명령 해시의 뜻)은 정의 확인이고, 이 폴더는 H-6·H-7 해시를 ③ 구분에 쓰지 않는다(태그·`extend_start_rule`로 구분, rev8 R8-1b 그대로). R11-6(G-S 출력 보관)은 실행 절차라 도구 코드가 없다. `p2_4368.py harness`의 4.2 대조는 H-1~H-10 줄(프리셋 켬·켬)만 다루고 H-0 줄은 `p2_t3k.py` 몫이라 기대값을 바꾸지 않았다. `p2_d1.py`·`p2_u3.py`에는 T4h 찾기와 4.2 스위치 대조가 없다 |

- 2026-11-13 G-S `…_130358`(`ba2da55`)에 `chrono --gs --git-at-start ba2da55`를 돌린 결과(참고, R11-7대로 인용하지 않음): 12행 가운데 11행 `code_at_launch` 일치, 열린 루프 1행(`GS_P3a_G1_B_VB_prop_lift10`) 기록 없음 → S-12(러너 기록 추가 전이라 예상된 결과). `code_state` 일치 9행, 없음 2행. `law_locked` SCM 9행·L2b 1행 통과, R10-2 출처 확인 12/12.
- 같은 실행에서 L1-R 행 `GS_D1C1_top_flat_crx3`의 `result.json`을 찾지 못했다(판정 불가 1건). L1-R 결과 폴더의 시각(`…_130359`)이 배치 시각(`…_130358`)보다 1 s 늦었기 때문이다. 이 문제는 이미 봉인된 rev7 R7-5에 규칙이 있었는데 경로 2가 반영하지 않았던 것이다. 아래 "rev7 R7-5 반영" 절에서 고쳤다.

### 도구 sha256 (rev11 판, LF 바이트)

- 이 표는 rev11 판(커밋 `582fa93`) 당시의 이력 값이다. **현재 값은 rev12 표**("rev12 반영" 절 "도구 sha256 (rev12 판)")에 있다.

| 파일 | sha256 | 이 판에서 |
|---|---|---|
| `p2_4368.py` | `4643dd407a9346db954b1db7e752c94f76fa1ed97e71d6cb78e5242af97d3a9b` | 바뀜 |
| `p2_d1.py` | `6d18f6dbfa891ea8faf2eec45cb26c023a045aa0170b7cfac4b1c0aa28cde24d` | 그대로 |
| `p2_t3k.py` | `f63cead31f6cde5dd23fe504370ec5c9f4101d7967c6eebc9aab3c08c642acf8` | 바뀜 |
| `p2_u3.py` | `408944c498da8736e343c2dbc2d816f6fdbe8a5ecd73a0a96689f06680bc5f28` | 그대로 |
| `p2_v5j.py` | `e5d769b925a1d3047a8f1a42443894f761520950d8d1ec75c31499e9ae7dd3fe` | 바뀜 |
| `test_p2_4368.py` | `4315553ec05d4c71c1a68c1ee2ecb5942ba806f9b1df5deaf643a1a6a94790c8` | 바뀜(111개) |
| `test_p2_d1.py` | `d1b61db2979ea1658eda4f515936e407a2d52666efeff9575c583dcecd0778ce` | 그대로(17개) |
| `test_p2_t3k.py` | `585384fa8693ff70703782349de4f0590a63782de5e886f4be32407ef0b962bf` | 바뀜(30개) |
| `test_p2_u3.py` | `245c03ff2a731fb33606f992328660f46f669dbee41cac4e20dc58b01133bb99` | 그대로(11개) |
| `test_p2_v5j.py` | `24d5141213a5daa01500809d0b5b62f373bc6c3a91c8c096cbb6f21d0c9f0ba7` | 바뀜(20개) |

- 자체 시험은 다섯 파일 189개(앞 판 168개)다. 더한 것(21개): `test_p2_4368.py` 6개(rev11 봉인과 불일치 S-1, 열린 루프 `code_at_launch` 일치·없음·다름, 7자리 약칭·짧은 값·인자 없음, level 행 `code_state` 일치·다름·없음), `test_p2_t3k.py` 11개(줄 종류 수와 R-0 끔·끔 통과, R-0 기록이 끔이면 S-3 아님, 결함 8가지, 요청 기록만·G-S S-11), `test_p2_v5j.py` 4개(찾는 곳 규칙, 한 번·여럿·없음·다른 실행 폴더, 재집계 S-2, CLI 입력 오류 S-11). 합성 H-0 줄에 `t3.bundle`과 `k1_order_gate_request`를 넣었고, 시험의 `run_main`이 `chrono`에 배치 기록 head를 `--git-at-start`로 넘긴다.
- `p2_4368.py`와 `p2_v5j.py`가 바뀌었으므로 `../path2_v5c/p2v5c_common.py`의 `P2_CORE_SHA`(`4643dd40…`)와 `P2_V5J_SHA`(`e5d769b9…`)를 고쳐야 한다(그 폴더 작성자 몫). `path2_v5c`가 단일 `--t4h-root`로 T4h를 읽는 부분(`p2v5c_stage1.judge_all`)도 R11-2 대상인지 그 폴더에서 판단해야 한다. `P2_CORE_SHA`는 아래 R7-5 반영으로 다시 바뀌었다.

## rev7 R7-5 반영 (L2b·L1-R 행 폴더, `v5_resume_4368_rules_rev7.md` 126·127행, 2026-11-13 rev11 판 뒤)

rev7 R7-5는 경로 1 집계 v2의 행 폴더 찾기를 정한 봉인 문장이다. 경로 2는 그때까지 `07_results/S6|S8/*<--tag>*<배치 시각>`처럼 시각이 정확히 같은 폴더만 찾았다. 그래서 러너 폴더 시각이 1 s 늦으면 행을 찾지 못했다. 이번에 같은 문장대로 바꿨다. 근거는 rev7 문장과 러너 기록 꼴(행 로그의 `batch wall … -> <폴더>` 줄, `progress.log`의 `START`·`END` 줄)뿐이다. 경로 1 코드는 열지 않았다.

| 항목 | 도구 | 반영 |
|---|---|---|
| 행 로그 | `p2_4368.py chrono`(`resolve_runner_row`) | L2b(`run_S8C.py`)·L1-R(`run_S6C.py`) 행 폴더 = `<배치>/<case>.log`의 **마지막** `batch wall … -> <폴더>` 줄의 폴더(`case_log`). `result.json`은 `<폴더>/<--only>/result.json`(없으면 `<폴더>/result.json`)이다 |
| 옮겨 찾기 | 같음 | 그 폴더에 `result.json`이 없으면 `<repo>/07_results/` 아래 같은 상대 경로(`07_results/` 뒤 부분)를 한 번 더 본다(`case_log_relocated`). 그래도 없으면 행을 판정하지 않고 **S-11** |
| 시각 창 | 같음 | 그 줄이 없으면 행 시각 창(`progress.log`의 그 case `START`~`END`, 없으면 배치 시각 + 행 `wall_s`) ±2 s 안에 시각이 든 러너 폴더(`07_results/S6`·`S8` 바로 아래, 이름 끝 `_<YYYYmmdd_HHMMSS>`, `result.json` 있음)를 찾는다. 하나뿐이면 그 폴더(`time_window`)를 쓰고, 없거나 둘 이상이면 판정하지 않고 **S-11** |
| 후보 범위(경로 2 읽기) | 같음 | "그 행의 러너 폴더"를 그 행 argv `--tag` 값이 이름에 든 폴더로 좁힌다. 같은 시각에 시작한 다른 행(예: `…_130359`의 L1-R과 L2b)의 폴더를 후보로 세지 않으려는 것이다. 같은 `--tag`의 다른 G-S 실행 폴더는 시각 창 밖이라 후보에 들지 않는다 |
| 기록 | 같음 | 행 `r75_folder`(`method`, `folder`, `case_log_target`, `window`, `candidates`, `why`), 출력 `R7-5_row_folders`(방법별 행). `batch.json`의 `s8c_check`·`s6c_check.result_json`이 찾은 폴더와 다르면 기록만 한다 |

- 2026-11-13 G-S `…_130358`에 `chrono --gs --git-at-start ba2da55`를 다시 돌린 결과(참고, R11-7대로 인용하지 않음): L1-R `GS_D1C1_top_flat_crx3`와 L2b `GS_D1C2_middle_fdown3.2_Fs4`의 폴더를 모두 `case_log`로 찾았다(`…_130359`). 판정 불가는 0건이다. 남은 멈춤은 열린 루프 행 `code_at_launch` 없음(R11-4, S-12) 1건뿐이다. `code_state`는 일치 9행, 없음 3행(L1-R 결과가 이제 읽혀 1행 늘었다).
- 자체 시험 194개(앞 절 189개). `test_p2_4368.py`에 5개를 더했다: 1 s 늦은 폴더를 행 로그로 찾음, 같은 tag의 다른 G-S 폴더와 혼동하지 않음, 결과 루트 아래로 옮겨 찾기, 로그 없음(시각 창 유일 후보 통과, 둘이면 S-11, 창 밖 제외, `progress.log` 우선), 로그 폴더에 결과 없음 S-11. 합성 L2b 배치는 이제 러너 폴더를 `<tmp>/07_results/S8/<tag>_<배치 시각 + 1 s>/<case>/`에 두고 행 로그로 가리킨다.

### 도구 sha256 (rev7 R7-5 반영 판, LF 바이트)

- 이 표는 R7-5 반영 판(커밋 `3eba3c5`) 당시의 이력 값이다. **현재 값은 rev12 표**("rev12 반영" 절 "도구 sha256 (rev12 판)")에 있다.

| 파일 | sha256 | 이 판에서 |
|---|---|---|
| `p2_4368.py` | `a8c625bf91184ec970a446a3997510ac2f8ce24df9d90b92b101b99b34a3fd43` | 바뀜 |
| `p2_d1.py` | `6d18f6dbfa891ea8faf2eec45cb26c023a045aa0170b7cfac4b1c0aa28cde24d` | 그대로 |
| `p2_t3k.py` | `f63cead31f6cde5dd23fe504370ec5c9f4101d7967c6eebc9aab3c08c642acf8` | 그대로 |
| `p2_u3.py` | `408944c498da8736e343c2dbc2d816f6fdbe8a5ecd73a0a96689f06680bc5f28` | 그대로 |
| `p2_v5j.py` | `e5d769b925a1d3047a8f1a42443894f761520950d8d1ec75c31499e9ae7dd3fe` | 그대로 |
| `test_p2_4368.py` | `daedbfb12f13f7c38a39a566dc154ac9c412e04dea975b3db6984d60b2a63b75` | 바뀜(116개) |
| `test_p2_d1.py` | `d1b61db2979ea1658eda4f515936e407a2d52666efeff9575c583dcecd0778ce` | 그대로(17개) |
| `test_p2_t3k.py` | `585384fa8693ff70703782349de4f0590a63782de5e886f4be32407ef0b962bf` | 그대로(30개) |
| `test_p2_u3.py` | `245c03ff2a731fb33606f992328660f46f669dbee41cac4e20dc58b01133bb99` | 그대로(11개) |
| `test_p2_v5j.py` | `24d5141213a5daa01500809d0b5b62f373bc6c3a91c8c096cbb6f21d0c9f0ba7` | 그대로(20개) |

- `../path2_v5c/p2v5c_common.py`: `P2_CORE_SHA` = `a8c625bf…`, `P2_V5J_SHA` = `e5d769b9…`로 맞춰야 한다(그 폴더 작성자 몫). `P2_CORE_SHA`는 아래 rev12 반영으로 다시 바뀌었다.

## rev12 반영 (`v5_resume_4368_rules_rev12.md`, sha256 `78f1f99b…`, 2026-11-13)

앞 절과 다른 곳은 아래가 맞다. 근거는 rev12 문장뿐이다(경로 1 코드·출력은 열지 않았다).

| rev12 | 도구 | 반영 |
|---|---|---|
| R12-6 봉인 확인 | `p2_4368.py`(`check_seals`, 다섯 도구 공통) | rev12 raw sha가 코드의 봉인 sha와 `.sha256` 첫 값 둘 다와 같고 LF·BOM 없음일 때만 통과(아니면 S-1, 종료 2). 출력 `seals.rev12_sha256` |
| R12-1 T4h 찾기 범위 | `p2_v5j.py u9` | 확인만 했다. 이 폴더에서 T4h를 읽는 판정은 `u9`의 J-P3 로드 판독뿐이고, 이미 R11-2 정의 1~3과 Q-R12-1 = A를 따른다. `t4h_file` 키가 없는 줄은 R3-C8 구성 규칙으로 읽고, 기록이 있는데 찾는 곳에서 0개 또는 2개 이상이면 S-2다. 라이브러리 함수 `rod_reading_from_t4h(line, t4h_root)`(단일 폴더, 못 찾으면 None)는 이 폴더의 판정에서 쓰지 않는다. `../path2_v5c`가 이름으로 부르므로 남겨 두었다. 그 폴더의 T4h 읽기는 R12-1 대상이다 |
| R12-2 dirty | `p2_4368.py chrono` | Chrono 행 `code_at_launch.git`의 `clean`·`dirty`·`paths`는 기록만 한다. 행 `launch_git_record`와 기록 "R12-2: dirty tree at launch recorded"를 남긴다. 앞 판은 `dirty`가 비어 있지 않으면 S-12였다 |
| R12-3 `--git-at-start` | `p2_4368.py chrono`(`--gs` 포함) | 필수다. 없거나 7자리보다 짧으면 입력 오류: 행을 하나도 판정하지 않고 S-11, 종료 2(출력 `input_error`, `batches_not_judged`). 앞 판은 없으면 판정 불가(종료 1)였다 |
| R12-4 열린 루프 `code_state` | `p2_4368.py chrono` | 열린 루프 행(C-6·C-7)의 `result.json` `code_state.git_at_start`는 기록만 한다(`code_state` = `openloop_record_same` / `openloop_record_differs`). 커밋 대조는 `code_at_launch.git.head`만이다 |
| R12-5 시각 창 대체 | `p2_4368.py`(`resolve_runner_row`, `runner_root`, `folder_name_re`) | 행 로그에 `->` 줄이 없을 때만 쓴다. 창은 `progress.log` START~END이고, 없으면 배치 시각 + `wall_s`다. `est_s`는 쓰지 않고, `wall_s`가 없으면 창을 정할 수 없다. 창 양 끝에 ±2 s를 둔다. 후보는 `run_S8C.py`면 `07_results/S8/` 바로 아래 이름이 정확히 `<tag>_<YYYYmmdd_HHMMSS>`, `run_S6C.py`면 `07_results/S6/` 바로 아래 이름이 `<기본>_<tag>_L1R_<stamp>`로 끝나는 폴더다(정규식 정확 맞춤, `_check_L1R_` 꼴 제외, 부분 문자열 맞춤 없음). 거기에 `<--only>/result.json`이 있어야 한다. 0개·2개 이상·창 불가·`--tag`/`--only` 없음은 입력 오류 S-11(종료 2)이다. 앞 R7-5 반영 판은 이름에 tag가 들어 있기만 하면 후보로 셌다 |

- 2026-11-13 G-S `…_130358`에 `chrono --gs --git-at-start ba2da55`를 돌린 결과(참고, R12-6대로 인용하지 않음): 판정 불가 0. L1-R·L2b 행은 `case_log`. 멈춤은 열린 루프 행 `code_at_launch` 없음(S-12) 1건으로 앞 판과 같다. `--git-at-start`를 빼면 S-11(종료 2, 행 0)이다.

### 사용자 결정 24 (2026-11-13, 최종 Y 감사): `t4h_file` 값 결함 = S-2

- `p2_v5j.rod_reading_lookup`은 줄에 `t4h_file` **키가 없을 때만** `no_t4h_file`(R3-C8 구성 규칙)로 본다. 키가 있는데 값이 None이거나 문자열이 아니거나 빈 문자열이면 `bad_t4h_file`로 보고 **S-2**로 멈춘다. 구성 규칙으로 대신하지 않는다(rev12 R12-1 Q-R12-1 = A의 취지, 경로 1·`path2_v5c`와 같은 읽기). 앞 판은 이 경우를 `no_t4h_file`로 읽었다. 출력 `H-5.R11-2_t4h_lookup`에 `bad_t4h_file` 수가 있다.
- 시험 `test_p2_v5j.py`에 1개를 더했다(키 없음 → 구성, None·숫자·빈 문자열 → S-2, 재집계 끝에서 끝). 다섯 파일 205개다.

### 도구 sha256 (rev12 판, LF 바이트, 현재 값)

- 결정 24 반영으로 `p2_v5j.py`·`test_p2_v5j.py`가 바뀌었다. 아래 표는 그 뒤의 값이다.

| 파일 | sha256 | 이 판에서 |
|---|---|---|
| `p2_4368.py` | `a948d9a138557f6a649ffd9a5b37cd018201525cb6d8a51480d3e449a2f9ca81` | 바뀜 |
| `p2_d1.py` | `6d18f6dbfa891ea8faf2eec45cb26c023a045aa0170b7cfac4b1c0aa28cde24d` | 그대로 |
| `p2_t3k.py` | `f63cead31f6cde5dd23fe504370ec5c9f4101d7967c6eebc9aab3c08c642acf8` | 그대로 |
| `p2_u3.py` | `408944c498da8736e343c2dbc2d816f6fdbe8a5ecd73a0a96689f06680bc5f28` | 그대로 |
| `p2_v5j.py` | `69d0e747254cea35196101a9a2fc1b0e3c4e6a15ba1cb4511a4c8c41ca3e25db` | 바뀜(결정 24) |
| `test_p2_4368.py` | `aa7bacde28111bfbf9e02bab05997a63e23a64b7f1b388069c639cc7b31d2158` | 바뀜(126개) |
| `test_p2_d1.py` | `d1b61db2979ea1658eda4f515936e407a2d52666efeff9575c583dcecd0778ce` | 그대로(17개) |
| `test_p2_t3k.py` | `585384fa8693ff70703782349de4f0590a63782de5e886f4be32407ef0b962bf` | 그대로(30개) |
| `test_p2_u3.py` | `245c03ff2a731fb33606f992328660f46f669dbee41cac4e20dc58b01133bb99` | 그대로(11개) |
| `test_p2_v5j.py` | `1380d01eb0c0f28bc13ff62c2b2276f225b679a2fb2ab895647b3415d9a67b2a` | 바뀜(결정 24, 21개) |

- 자체 시험은 다섯 파일 204개다(앞 판 194개). `test_p2_4368.py`에 10개를 더했다. 더한 것은 rev12 봉인과 불일치 S-1, dirty 기록만, 열린 루프 `code_state` 기록만, 폴더 이름 정확 맞춤(L1-R `_check_L1R_` 제외, 부분 문자열·접두 없음, L2b 다른 tag), L1-R 시각 창 6가지(통과, 확인 실행 무시, 후보 둘, 없음, `est_s` 미사용, `wall_s` 없음)다. `--git-at-start` 없음·짧음 시험은 R12-3에 맞게 입력 오류로 고쳤다. C-2 고정 행 시험에도 이 인자를 준다.
- `../path2_v5c/p2v5c_common.py`: `P2_CORE_SHA` = `a948d9a1…`, `P2_V5J_SHA` = `69d0e747…`로 맞춰야 한다(그 폴더 작성자 몫).

## 하지 않는 것 (범위)

- **원 규칙 등급의 재집계는 하지 않는다.** H-0 T-3K(`las_targeted_rules` 원판~rev5), H-1·H-2(D-1 선별 규칙), H-3·H-4(`u3_u6`), H-5(`u9`), H-6~H-10(v5 기준 + 개정 1~12b), C-1~C-5 판정 블록(D-1 규칙 11, 개정 12 2.2)의 통과·미달 재집계가 여기에 든다. 이 도구가 내는 묶음 상태는 436.8 문서가 새로 정한 층(4.1·4.2·6·7.2·7.4·9.3·S-15)의 상태다(`grade_scope`). 원 규칙 등급의 경로 2는 그 규칙들의 정의 문장을 읽고 따로 만들어야 한다.
- 결과를 만들거나 하네스·Chrono를 실행하지 않는다. 읽기만 한다.

## 실행 예

```powershell
$t = '<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2\p2_4368.py'
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\seal.json seal
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\h.json harness --manifest <out>\manifest.json
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\a.json anchors --h1 <repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1\h1_d1.jsonl
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\c.json chrono --batch <repo>\07_results\S9\batch_V5-RESUME-K1-C5_<stamp> --check-counts --rows-manifest <repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\chrono_rows_manifest.json --git-at-start <판정서 git_at_start>
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\gs.json chrono --batch <repo>\07_results\S9\batch_V5-RESUME-K1-GS_<stamp> --gs --rows-manifest <repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\chrono_rows_manifest.json --git-at-start <최종 Y 커밋>
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\jp.json jp --shadow <repo>\06_analysis\03_hydraulic\coupled\v5\las\shadow_jp_b0.jsonl --batch <repo>\07_results\S9\batch_V5-JP-VB_20261108_115631 --batch <repo>\07_results\S9\batch_V5-JP-V0_20261108_131212
```

- `conda run`은 stdout을 cp949로 다시 인코딩하므로 요약 줄은 ASCII다. 본문은 `--out` JSON(UTF-8, LF)에 쓴다.
- 판정에 쓰는 출력은 경로 1 출력과 대조하기 전에 sha256(`out_sha256`)을 판정서에 적는다(9.2 순서).

## 자체 시험

```powershell
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider --basetemp <scratch>\pt <repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2\test_p2_4368.py
```

- `test_p2_4368.py`는 126개(rev12 판, rev7 R7-5 반영 판 116개, rev11 판 111개, rev10 판 105개, rev9 판 89개, rev8 판 65개, 처음 판은 45개), 합성 입력만 쓴다(봉인 확인 시험은 저장소의 실제 규칙 파일을 읽는다). 합성 배치는 폴더 옆에 자기 `rows_manifest.json`을 두고, 시험의 `run_main`이 `chrono`에 `--rows-manifest`로 넘긴다. rev3~rev10에서 더한 시험은 각 판 절에 있다. 다루는 것: 문턱 비교와 K-10, $R_c$ 식, `C2Event` 해석, 줄 키, 지면 계열, 7.2 분류 9가지(S-5·S-6·S-3 포함), 결측 = 판정 불가, C-4 끔 팔 'LAS 없음', LAS-b 설정 검사, 하네스 끝에서 끝(통과, S-2, S-5 + S-6, IND 해당 없음 + S-3 토큰, S-15), 1 ms 재계산(이탈 지속 조건, 창 시간), Chrono 행(O-C5 S-9, S-10, 태그 S-2, 금지 인자 S-3 + 스레드 S-4, C-4 끔 팔), O-C5 $k$ 절차(첫 probe, 할선, 두 배 재실행, 할선 정의 불가), J_P 재사용과 거부, K-10 compare, 실제 규칙 sha.

## 독립성 공개 (규칙 9.2, 이 도구를 쓰려고 읽은 것)

- 규칙: 원판, rev1, rev2, `d1_selection_rules.md`·rev1, `u3_u6_rerun_rules.md`·rev1·rev2, `las_p5r4_k1_judgement.md` 8.2절 표·1.1의 기호 정의(40행), 명세 `s6_control_spec.md` 436 설정 표(19458~19479행).
- 원 데이터(키 구조와 식별 필드): G-S 배치 `batch_V5-RESUME-K1-GS_20261113_010654`·`_012403`·`_020211`의 `batch.json`과 행 `result.json`·npz 키 이름(값은 판정에 쓰지 않음), 저장 P5r4 A1 `result.json`의 정의 문자열(`P3-3_leg_force.criterion`, `p3b.departure.rule`, `start_condition.rule`, `basis`), 저장 J_P 배치 `batch.json`과 `controller_events.json` 형식, `shadow_jp_b0.jsonl` 형식, 저장 `d1.jsonl`·`u3_slope_V0.json`·`noise_vb/r79_VB_L1L2L3.json`·`grid_vb/grid_r67_main.json`·`dg3/dg3_v4_on.json`의 컨테이너 구조와 키 이름.
- 코드: `03_src/outrigger_sim/hydraulics/v5_options.py`(태그 상수와 `is_extend_start_tag`, 4.1이 지정), `06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/openloop_compare.py`(`analyse`, 9.1이 지정), 선례 `verif_matrix/p5k_path2/p5k_chrono_recount.py`의 머리 주석과 상수 이름(다른 판정의 경로 2, 436.8 경로 1 아님).
- 보지 않은 것: `verif_matrix/scripts/resume4368_judge.py`, `04_scripts/04_hydraulic/coupled/u3_judge_k1.py`, `resume_k1_record.py`, `resume_k1_steps.py`, `verif_matrix/v5_resume_4368/gs_check_*.txt`·`chrono_rows_check.json`(경로 1 또는 행 생성기 출력일 수 있어 열지 않음), 행 정의 모듈 `v5_resume_4368_chrono_rows.py`, 러너 코드.
- rev9 판에서 더 읽은 것: `v5_resume_4368_rules_rev9.md`. `chrono_rows_manifest.json`은 rev8 판까지 열지 않았다. rev9 R9-4가 LS 판별의 입력으로 정했으므로(두 경로 공통 입력) 이 판에서 도구 입력으로 쓴다. 작성 중에 사람이 본 것은 키 구조뿐이다: 최상위 키, `batches`의 묶음 이름, 묶음의 키(`rows` 등), 행 키 이름, `v5_setting` 값 집합(`LS1`·`LS4`·`None`·`S6SEED`·`V0`·`V0v`·`VB`). 행별 값은 보지 않았다. 참고 실행(G-S `…_082117`)의 행 결과는 판정에 쓰지 않는다.
