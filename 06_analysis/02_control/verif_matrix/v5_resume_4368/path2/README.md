# 436.8 경로 2 독립 재집계 도구 (`p2_4368.py`)

- 규칙: 원판 `../../v5_resume_4368_rules.md`(sha256 `9019b405…`)와 rev1 `../../v5_resume_4368_rules_rev1.md`(sha256 `d9094fda…`). 둘이 다르면 rev1을 따른다. 도구는 실행할 때마다 두 파일의 sha256, `.sha256` 기록, LF·BOM 없음을 확인한다. 하나라도 어긋나면 **종료 2(S-1)**로 멈춘다. 부록 A 33개 파일도 같이 확인한다. 이때 `core.autocrlf` checkout이라 줄바꿈만 다른 경우(LF로 바꾼 sha가 기록과 같음)는 통과로 두고 `eol_only`에 남긴다.
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
| `would_block` 참 ∧ `r4_due` 거짓 | 어느 분류에도 들지 않음 → `판정 불가` | 7.2 문장에 없음(확인 필요 1) |
| `_SKIPPED:order` 수 | 줄 `events`(전체 목록일 때) → `event_names` 개수 → `resume_k1.event_counts.flat_soil_margin_skipped_order` 순. Chrono는 `events[]`, 없으면 `controller_events.json`. 이름 완전 일치 | 7.2, 7.3-3 |
| 지면 계열 | `@`가 든 토큰(패치 `토양@다리`, 처방 침하 `c-mid@다리`) → 패치·처방. `rigid` 토큰 → 강체. 토양 이름(G1·G5·J1·J2·S1·S2)만 → 균일 연약. 그 밖 → 미분류. D-1은 `job.d1`의 `base`·`patch_leg`·`patch_soil`·`sink`를 먼저 본다. Chrono: L2b·L1-R → 강체, `rigid_base`·`soil_patch` → 패치, `soil`만 → 균일 | 7.2, RV1-6(경로 1 계열 표는 쓰지 않음) |
| 미분류 + K1 막힘 | 균일과 같게 S-6 | RV1-6("나누지 못한 키는 균일 연약") |
| `applicable` 거짓 | IND·IND_LAS에서는 "해당 없음"으로 세고 분류·4.2 확인을 하지 않는다. 다른 종류 줄이면 S-3 | RV1-6 덧붙임 |
| LAS-b 설정 9값 | `enable` True, `sum_on_fraction_W` 0.6, `light_leg_fraction_of_F_min` 3.5, `slow_mean_fraction` 0.16, `sum_off_fraction_W` 0.85, `off_periods` 5, `max_s` 1.5, `rho_on` 0.18, `require_soil_response` True(ABL은 False). 키 `min_active_periods`·`end_ramp_periods`가 있으면 0이어야 한다(P0) | 4.2, 명세 436 설정 표 |
| L2b·L1-R 4.2 확인 | 결과에 `c2_setup`이 없으면 요청 = argv(`--k1-order-gate` 없음 = `preset`), 적용 = `order_gate.enabled` | 4.2 "같은 의미"(확인 필요 4) |
| 이탈 시각 $t_d$ | `step_series.npz`의 `scm_crawler_normal_N` < 0.01 `p3b.weight_N`이 0.1 s 이상 이어지는 첫 구간의 첫 표본 | `p3b.departure.rule` 문자열(P3a-2) |
| $F^{a}_{min}$ | $t \ge t_d$의 1 ms `F_cyl_N` 다리별 최소 | 2절 기호 표 |
| $F<F_{min}$ 시간, $F<F_{min}$+2 kN 시간 | $[t_d, t_d + 8\,\mathrm{s}]$ 안에서 조건을 만족하는 표본 수 × $\Delta t$(중앙값). 비교 허용 $10^{-9}$ N(7.6) | P5r4 판정서 8.2 표("이탈 + 8 s 창"), RV1-7 |
| O-C5 $m$·멈춤 | $R_c \le 1$일 때 경로 2 $m$(1 ms 재계산 최소) < $F_{min}$ → S-9, $< F_{min}$+2000 N → 여유 기록, 그 밖 기록. `result.json` 최소로 정한 등급도 함께 내고, 다르면 기록 | 7.4, RV1-7 |
| $R_c$ | 기록된 `crawler_attitude_deg`로 $\lvert\phi_c\rvert/4.4 + \lvert\theta_c\rvert/3.2$ 재계산. 기록값과 K-10 허용 밖이면 기록 | 2절, 9.1 C-8 |
| 열린 루프 | `openloop_compare.py`의 `first_run`·`plane_fit`·`analyse`와 상수 `F_MIN`·`T_LIFT`·`PAD_XY`만 AST로 꺼내 실행한다(모듈 끝의 저장 행 실행은 하지 않음). 속도비는 `analyse`에 계산식이 없어 경로 2 가정으로 낸다: 창 양 끝의 `s_motor` 차 / 시간 / `flow_limit.circuit.max_speed_m_s`, 다리별·평균, 창 8.5 s < t ≤ 끝과 10~20 s 둘 | 5.3, 9.1(확인 필요 5) |

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

## 하지 않는 것 (범위)

- **원 규칙 등급의 재집계는 하지 않는다.** H-0 T-3K(`las_targeted_rules` 원판~rev5), H-1·H-2(D-1 선별 규칙), H-3·H-4(`u3_u6`), H-5(`u9`), H-6~H-10(v5 기준 + 개정 1~12b), C-1~C-5 판정 블록(D-1 규칙 11, 개정 12 2.2)의 통과·미달 재집계가 여기에 든다. 이 도구가 내는 묶음 상태는 436.8 문서가 새로 정한 층(4.1·4.2·6·7.2·7.4·9.3·S-15)의 상태다(`grade_scope`). 원 규칙 등급의 경로 2는 그 규칙들의 정의 문장을 읽고 따로 만들어야 한다.
- 결과를 만들거나 하네스·Chrono를 실행하지 않는다. 읽기만 한다.

## 실행 예

```powershell
$t = '<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2\p2_4368.py'
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\seal.json seal
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\h.json harness --manifest <out>\manifest.json
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\a.json anchors --h1 <repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1\h1_d1.jsonl
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\c.json chrono --batch <repo>\07_results\S9\batch_V5-RESUME-K1-C5_<stamp> --check-counts
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B $t --out <out>\jp.json jp --shadow <repo>\06_analysis\03_hydraulic\coupled\v5\las\shadow_jp_b0.jsonl --batch <repo>\07_results\S9\batch_V5-JP-VB_20261108_115631 --batch <repo>\07_results\S9\batch_V5-JP-V0_20261108_131212
```

- `conda run`은 stdout을 cp949로 다시 인코딩하므로 요약 줄은 ASCII다. 본문은 `--out` JSON(UTF-8, LF)에 쓴다.
- 판정에 쓰는 출력은 경로 1 출력과 대조하기 전에 sha256(`out_sha256`)을 판정서에 적는다(9.2 순서).

## 자체 시험

```powershell
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider --basetemp <scratch>\pt <repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2\test_p2_4368.py
```

- 41개 시험, 합성 입력만 쓴다. 다루는 것: 문턱 비교와 K-10, $R_c$ 식, `C2Event` 해석, 줄 키, 지면 계열, 7.2 분류 9가지(S-5·S-6·S-3 포함), 결측 = 판정 불가, C-4 끔 팔 'LAS 없음', LAS-b 설정 검사, 하네스 끝에서 끝(통과, S-2, S-5 + S-6, IND 해당 없음 + S-3 토큰, S-15), 1 ms 재계산(이탈 지속 조건, 창 시간), Chrono 행(O-C5 S-9, S-10, 태그 S-2, 금지 인자 S-3 + 스레드 S-4, C-4 끔 팔), O-C5 $k$ 절차(첫 probe, 할선, 두 배 재실행, 할선 정의 불가), J_P 재사용과 거부, K-10 compare, 실제 규칙 sha.

## 독립성 공개 (규칙 9.2, 이 도구를 쓰려고 읽은 것)

- 규칙: 원판, rev1, `las_p5r4_k1_judgement.md` 8.2절 표·1.1의 기호 정의(40행), 명세 `s6_control_spec.md` 436 설정 표(19458~19479행).
- 원 데이터(키 구조와 식별 필드): G-S 배치 `batch_V5-RESUME-K1-GS_20261113_010654`·`_012403`·`_020211`의 `batch.json`과 행 `result.json`·npz 키 이름(값은 판정에 쓰지 않음), 저장 P5r4 A1 `result.json`의 정의 문자열(`P3-3_leg_force.criterion`, `p3b.departure.rule`, `start_condition.rule`, `basis`), 저장 J_P 배치 `batch.json`과 `controller_events.json` 형식, `shadow_jp_b0.jsonl` 형식, 저장 `d1.jsonl`·`u3_slope_V0.json`·`noise_vb/r79_VB_L1L2L3.json`·`grid_vb/grid_r67_main.json`·`dg3/dg3_v4_on.json`의 컨테이너 구조와 키 이름.
- 코드: `03_src/outrigger_sim/hydraulics/v5_options.py`(태그 상수와 `is_extend_start_tag`, 4.1이 지정), `06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/openloop_compare.py`(`analyse`, 9.1이 지정), 선례 `verif_matrix/p5k_path2/p5k_chrono_recount.py`의 머리 주석과 상수 이름(다른 판정의 경로 2, 436.8 경로 1 아님).
- 보지 않은 것: `verif_matrix/scripts/resume4368_judge.py`, `04_scripts/04_hydraulic/coupled/u3_judge_k1.py`, `resume_k1_record.py`, `resume_k1_steps.py`, `verif_matrix/v5_resume_4368/gs_check_*.txt`·`chrono_rows_check.json`·`chrono_rows_manifest.json`(경로 1 또는 행 생성기 출력일 수 있어 열지 않음), 행 정의 모듈 `v5_resume_4368_chrono_rows.py`, 러너 코드.
