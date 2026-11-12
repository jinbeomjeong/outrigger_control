# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev2 (두 경로 해석 통일 9항, 결과 전, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev2.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev2_seal_candidate_draft.md`와 1·3·5행만 다르다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524`)와 rev1 `v5_resume_4368_rules_rev1.md`(sha256 `d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7`)는 고치지 않는다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 2026-11-13 02:30:11 +09:00, 봉인 커밋 316fd8a).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 Chrono G-S 배치 3개뿐이다(R2-0).
- 작성: control-expert, 2026-11-13. 기준 master `316fd8a`(작성 시점 HEAD, rev1 봉인 커밋). 계기: 두 경로 작성자가 규칙 문장만으로 정할 수 없다고 낸 해석 9항과 사용자 결정(2026-11-13).
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위(원판 8.1), 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측의 예측 값, 두 경로 요건(원판 9.2). 이 판은 정의 문장만 정한다. 두 경로가 같은 문장에서 같은 답을 내도록 하는 것이 목적이다.
- 이 판은 경로 2 작성자에게 주는 규칙 문장이다. 구현 세부(도구 이름·함수·코드 위치)는 쓰지 않았고, 정의의 원본은 봉인 규칙·명세·이전 판정서의 문장과 결과 파일의 필드 이름뿐이다.

## R2-0. 결과 전 근거와 공개

- 2026-11-13 main checkout(`316fd8a`) 확인: `06_analysis/03_hydraulic/coupled/v5/resume_k1/`, `06_analysis/02_control/v5_rerun/las_k1/`, `06_analysis/03_hydraulic/coupled/v5/las/t3_k1/`이 없다. `07_results/S9/`에서 이름에 `RESUME-K1`이 든 폴더는 G-S 배치 `…_20261113_010654`, `…_012403`, `…_020211` 세 개뿐이다. G-S는 판정하지 않는다(원판 11.2). 이 작성자는 G-S 값을 읽지 않았다.
- 이 판을 쓰려고 읽은 것:
  - 규칙: 원판, rev1, `las_k1_rules.md` 62~66행(K1 결정 필드 정의), `las_p5r4_k1_judgement.md` 40~41행·326~337행(이탈 뒤 창의 정의).
  - 명세 `00_docs/04_control/s6_control_spec.md` 11025행(P3-2의 t_D), 11820행·11836행(이탈 시각 정의), 342.1~342.2절(r67 축소 스크린 하네스와 사건), 19656행(K1 결정 기록).
  - 판정서 `06_analysis/03_hydraulic/coupled/v5/v5_paper_runs_judgement.md` 101행·124행·127행·147행·156행(열린 루프 속도비의 기존 정의 문장).
  - 저장 격자 결과 `v5/grid_vb/grid_*.json` 4개의 식별 필드(`meta.spec`, `meta.script`, `results[].key`, `runs[].event`)만. 값은 읽지 않았다.
  - 제어기 기록 정의를 확인하려고 `03_src/outrigger_sim/control/c2.py`의 K1 결정 기록과 LAS-b 기록을 읽었다. 이 판의 문장은 그 내용이 아니라 위 규칙·명세 문장을 원본으로 삼는다.
- 이 작성자는 rev1을 쓰며 경로 1 코드를 읽었으므로 436.8의 경로 2 작성자가 아니다. 경로 2는 하네스 H-0~H-10을 dynamics-expert, Chrono C-1~C-5 판정 블록 재계산을 새 control-expert 인스턴스가 맡는다(사용자 결정 2026-11-13).

## R2-1. `would_block` 참 ∧ `r4_due_without_gate` 거짓 (항목 1)

- 정의: `las_k1_rules.md` 63행에 따라 `would_block` = `r4_due_without_gate` ∧ (n_P ≤ n_S 또는 t_P·t_S 없음)이다. 그러므로 `would_block`이 참이면 `r4_due_without_gate`도 참이어야 한다.
- `decisions` 항목 가운데 `would_block` 참 ∧ `r4_due_without_gate` 거짓인 것은 **기록 모순**이다. 원판 7.2의 어느 분류에도 넣지 않는다.
  - 그 줄·행은 `판정 불가`다.
  - 그 묶음은 원판 8.2 **S-5**로 멈추고 묻는다(`applied` ∧ `would_block`과 같은 기록 모순 처리).
- 두 경로 모두 이 문장으로 처리한다. "분류 밖 → 멈춤"과 "판정 불가"는 이 판에서 하나가 된다: 그 줄은 `판정 불가`, 그 묶음은 S-5.
- 같은 정의로, `applied` 참 ∧ `r4_due_without_gate` 거짓도 기록 모순으로 S-5다(R4c30은 due일 때만 적용된다).

## R2-2. `liftoff_approach_slow.start_s`가 없을 때 (항목 2)

하네스 줄과 Chrono 행에 같이 적용한다. 대상 블록은 하네스 줄이 `resume_k1.liftoff_approach_slow`, Chrono 행이 `controller_meta.liftoff_approach_slow`다.

| 기록 상태 | 원판 7.2의 읽기 |
|---|---|
| 블록이 있고 `start_s` 키가 있으며 값이 None | LAS-b 시작 안 함 |
| 블록이 있고(`settings`가 있음) `start_s` 키가 없음 | **LAS-b 시작 안 함**(LAS-b 상태가 생기지 않은 실행의 기록. 결측으로 보지 않는다) |
| 블록이 있고 `start_s`가 수 | LAS-b 작동 |
| 블록 자체가 없음 | `판정 불가`(원판 9.3 결측) |
| C-4 끔 팔(`--las-off`) | 'LAS 없음'(rev1 RV1-10 b). 블록이 없어도 결측이 아니다 |
| `resume_k1.applicable` 거짓(IND·IND_LAS) | 해당 없음(rev1 RV1-6) |

- "LAS-b 시작 안 함"은 원판 7.2 미작동 조건의 앞 절(`start_s` = None)을 만족하는 것으로 읽는다. `end_s`·`end_reason`이 없는 것도 같은 읽기다.

## R2-3. L2b·L1-R 결과에 `c2_setup`이 없을 때 (항목 3)

L2b(`run_S8C.py`)와 L1-R(`run_S6C.py`) 결과의 원판 4.2 기록 확인은 다음 필드로 읽는다.

| 원판 4.2 키 | L2b·L1-R에서 읽는 곳 | 기대 |
|---|---|---|
| `c2_setup.k1_order_gate`(요청) | 그 행 argv(`batch.json` 행의 argv) | argv에 `--k1-order-gate`가 없으면 `preset`. 있으면 원판 4.2 위반(S-3) |
| `c2_setup.k1_order_gate_effective`(적용) | `result.json` `controller_meta.slope_clearance_margin.order_gate.enabled` | true |
| `flat_soil_margin_order_gate` | `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate` | true(원판 그대로) |
| `liftoff_approach_slow.settings` 9값 | `controller_meta.liftoff_approach_slow.settings` | 프리셋 값(원판 그대로) |
| `c2_setup.las_off` | 해당 없음(L2b·L1-R에는 끔 팔이 없다) | – |

- `controller_meta`가 없거나 위 키가 없으면 그 행은 `판정 불가`(원판 9.3)이고 S-3을 검토한다.
- 태그 확인은 argv의 `--expect-controller`와 결과의 태그 기록으로 한다(rev1 RV1-10 a).

## R2-4. C-6·C-7 속도비 정의 (항목 4)

원판 5.3의 "속도비"에는 계산식이 없다. 이 판은 **이전 판정서의 기존 정의 문장**을 그대로 쓰고, 두 양을 이름으로 나눈다. 원본은 `v5_paper_runs_judgement.md`다.

| 양 | 정의(원문 인용) | 출처 | 쓰는 행 |
|---|---|---|---|
| r_vu 유량 속도비 | "속도비는 `flow_series.npz` 1 ms 행의 v/u(8.5 s < t ≤ 36 s, u ≥ 0.1 v_max)"(101행). 창 끝은 "속도비 창은 8.5 s < t ≤ 실행 끝이다(36 s 고정에서 바꿨다)"(147행). 보고 값은 "속도비 v/u 중앙값 FL / FR / RL / RR"(124행) | 1.6절·1.7절 | C-6, C-7a(VB, 유량 기록이 있는 행) |
| r_v 신장 속도비 | "신장 속도 / v_max(측정)"(156행), 비고 "V0_FB는 10~20 s ṡ_motor"(156행). 같은 창의 "무부하 신장 속도 10~20 s"(127행) | 1.7절 | C-6, C-7a, C-7b |

- 계산(두 경로 같음):
  - r_vu: 다리마다 `flow_series.npz`의 1 ms 행 가운데 8.5 s < t ≤ 실행 끝 ∧ u ≥ 0.1 v_max인 행의 v/u 중앙값. v = 그 다리의 실제 신장 속도, u = 명령 속도.
  - r_v: 다리마다 10 s ≤ t ≤ 20 s 구간에서 s_motor의 구간 첫 표본과 끝 표본의 차를 두 표본 시각 차로 나누고 v_max로 나눈 값.
  - 공통: 시각은 결과 파일의 절대 시뮬레이션 시각(정착 8 s 포함)이다. v_max = YAML `actuator.max_speed_m_s`이다. 네 다리 값을 모두 적는다.
- 사전 예측의 대응(봉인된 예측 값과 그 근거 문장으로 정한 것이다. 저장 결과로 맞춘 것이 아니다):
  - P-10 "속도비 0.8947 ± 0.001"은 r_vu다. 근거는 124행 "속도비 v/u 중앙값 … 0.8947 × 4"다.
  - P-11·P-11b "속도비 0.8769"는 r_v다. 근거는 156행 "신장 속도 / v_max(측정) … 0.8769"다.
- C-7b(V0)에는 유량 기록이 없으므로 r_vu가 해당 없다(원판 5.3 "V0라 유량 항목 해당 없음").
- 원판 5.3 표의 "`openloop_compare.py`의 `analyse` 정의(속도비 창 8.5 s < t ≤ 실행 끝)"는 r_vu의 창으로 읽는다.
- 창 양 끝 s_motor 차를 8.5 s~실행 끝 시간으로 나눈 양은 이 판의 속도비가 아니다. 기록하더라도 P-10·P-11 대조에 쓰지 않는다.

## R2-5. `F<F_min` 시간의 창 (항목 5)

- 이탈 시각 t_D = `step_series.npz`의 크롤러 참 법선(1 ms)이 0.01 W 미만으로 0.1 s 이상 이어지는 첫 구간의 첫 표본 시각이다. W = `result.json` `p3b.weight_N`이다. 원본은 명세 11025행("t_D = 크롤러 SCM 법선 < 0.01 W가 0.1 s 이어진 구간의 시작")과 11820행·11836행이다. 혼합 지형 행은 크롤러의 모든 접촉 법선의 합을 쓴다.
- 기록 창 = [t_D, t_D + 8 s]. 원본은 `las_p5r4_k1_judgement.md` 41행(`F_min_transient_N`, "이탈 + 8 s까지")과 326행("1 ms 참 F_cyl … 이탈 + 8 s 창")이다. 실행이 창 끝 전에 끝나면 실행 끝까지이고, 그 사실을 적는다.
- 시간 값(원판 7.4 기록 항목):
  - `F<F_min` 시간 = 창 안에서 다리별 1 ms 참 F_cyl < F_min인 표본 수 × 1 ms. 원판 7.6 비교 허용을 쓴다.
  - `F<F_min+2 kN` 시간 = 같은 정의로 F_cyl < F_min + 2000 N.
  - 다리별 값과 네 다리 최대를 적는다.
- 같은 두 시간을 t_D 뒤 실행 끝까지의 전체 창으로도 계산해 **기록만** 한다. L-5 문장과 사전 예측 대조에는 8 s 창 값을 쓴다.
- t_D가 정의되지 않으면(조건을 만족하는 구간이 없음) 두 시간은 `판정 불가`(결측)이고 그 사실을 적는다.

## R2-6. S-9 판정 값과 두 경로 (항목 6)

원판 7.4의 m(네 다리 이탈 뒤 최소)을 두 경로가 각각 낸다.
- 경로 1: `result.json` `p3b.P3-3_leg_force.F_min_after_N`의 네 다리 최소(rev1 RV1-7).
- 경로 2: `step_series.npz` 1 ms 참 F_cyl의 t ≥ t_D(R2-5 정의) 다리별 최소의 네 다리 최소(원판 9.1 C-8).

처리:
1. 각 경로가 원판 7.4 표의 처리 칸 하나를 낸다: 멈춤 / 여유 기록 / 기록.
2. 두 경로의 처리 칸이 같고 m이 원판 9.2 K-10 허용 안에서 같으면, 그 처리를 따른다. 판정서·L-5에는 경로 1 값을 적고 경로 2 값을 함께 적는다.
3. 처리 칸은 같은데 m이 K-10 허용 밖이면, 그 처리를 따른다. 두 값을 적고 python-expert에 원인 확인을 넘긴다(원판 9.2 "등급은 같고 수치만 허용 밖").
4. **처리 칸이 다르면** 그 행은 `판정 불가`(원판 8.2 S-13에 준함)이고 멈춘 뒤 묻는다. 두 값과 두 처리를 그대로 적는다. 판정서 종합 문장과 L-5는 결정 뒤에 쓴다.
5. 어느 한 경로라도 m < F_min이면 그 행은 결정 전까지 S-9 멈춤으로 다룬다. 4와 같이 걸리면 한 번에 묻는다.

## R2-7. 격자(r67·r69) 줄의 지면 계열 (항목 7)

격자 결과의 키(`screen|<오거>|<F_s>|level|<다리>`)에는 지면 토큰이 없다. 계열은 다음 식별 필드로 정한다(rev1 RV1-6의 계열 표 규칙에 더한다).

| 조건 | 계열 |
|---|---|
| 파일 `meta.spec` = `rev. 67 (G1 / G2 / G7 reduced screen)` ∧ 그 run의 `event`가 `G4`·`RE1bF`·`FS24` 가운데 하나 | **패치·처방 침하**(강체 바닥 축소 하네스에 처방 바닥 사건, 명세 342.1·342.2) |
| `meta.spec`이 위와 다르거나 없음, 또는 `event`가 없거나 위 셋 밖 | 분류 안 됨 → 균일 연약으로 다룬다(그 run의 K1 막힘은 **S-6**, rev1 RV1-6) |

- 계열은 run 단위(`results[].runs[]`)로 정한다. 같은 `results[]` 항목의 run들은 키를 공유하지만 `event`가 다를 수 있다.
- 두 경로 모두 이 표만 쓴다. 키 문자열에서 지면을 추측하지 않는다.
- 2026-11-13 저장 VB 격자 4파일의 식별 필드(값 아님)는 모두 첫 줄 조건을 만족했다(`meta.spec` 같음, `event` 셋 각 64 run/파일).

## R2-8. C-2 고정 행 수 (항목 8)

- 받아들인다. 원판 5.2 C-2 "4(L2b C2-03·07, SCM S-01·02)"는 고정 행이다. C-2에 H-2 선별이 정한 행 가운데 이 네 행이 정확히 다 있지 않으면(4가 아니면) **S-15**로 멈추고 묻는다.
- 이 검사는 rev1 RV1-10 g의 세 검사와 함께 본다: 기준선 실패 추가 행 0~4, PS-c 행 0~2, 합 4~10. 넷 가운데 하나라도 어긋나면 S-15다.

## R2-9. S-1 줄바꿈 정규화 (항목 9, 사용자 결정 2026-11-13)

- 원판 8.2 S-1의 sha256 대조 대상은 원판 부록 A의 파일들이다.
- raw sha256이 기록과 다를 때는 그 파일의 CRLF를 모두 LF로 바꾼 바이트의 sha256을 계산한다. 그 값이 기록과 같으면 S-1을 통과로 본다. 다른 바이트 변경은 허용하지 않는다.
- 통과한 경우 판정서에 파일 이름, raw sha256, LF 정규화 sha256, 그리고 "CRLF 변환만 다름"을 적는다(공개).
- 정규화해도 다르면 원판대로 S-1(전 묶음 멈춤)이다.
- 봉인 규칙 파일 자체(원판, rev1, 이 판)는 `-text`로 보호되므로 raw sha256으로만 대조한다.
- `las_p5r4_k1_judgement.md`에 `-text` 보호를 더하는 일은 메인 세션이 이 판을 봉인할 때 한다(끝 절 6). 그 전에 이 파일이 CRLF로 바뀌었으면 위 정규화 규칙으로 대조한다.

## R2-10. 사용자 결정 기록 (결과 전)

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-13 | 경로 2 배정 | 하네스 H-0~H-10 원 규칙 등급 재집계 = dynamics-expert, Chrono C-1~C-5 판정 블록 재계산 = 새 control-expert 인스턴스. rev1 작성자는 경로 2를 맡지 않는다 | R2-0 |
| 2026-11-13 | S-1 줄바꿈 | LF 정규화 sha가 기록과 같으면 통과, 판정서에 공개. `las_p5r4_k1_judgement.md`에 `-text` | R2-9 |
| 2026-11-13 | 해석 1~8 | 두 경로 해석을 이 판의 한 가지 문장으로 정한다 | R2-1~R2-8 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev2_seal_candidate_draft.md` → `v5_resume_4368_rules_rev2.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev2 (두 경로 해석 통일 9항, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev2.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev2_seal_candidate_draft.md`와 1·3·5행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev2.sha256`에 `<sha256>  v5_resume_4368_rules_rev2.md  sealed <SEAL_TIME 값> (436.8 rev2: two-path interpretations unified before results; would_block record conflict = S-5, absent start_s = not started, L2b/L1-R K1 record fields, open-loop speed ratio definitions quoted, F<F_min window t_D + 8 s, S-9 two-path handling, grid family by meta.spec + event, C-2 fixed 4 rows, S-1 CRLF normalisation; thresholds and grades unchanged)` 한 줄로 쓴다.
6. `.gitattributes`에 다음을 더한다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev2.md -text`
   - `…/v5_resume_4368_rules_rev2.sha256 -text`
   - `…/v5_resume_4368_rules_rev2_seal_candidate_draft.md -text`
   - `06_analysis/02_control/verif_matrix/las_p5r4_k1_judgement.md -text`(R2-9)
7. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev3.md`로 새로 봉인한다.
