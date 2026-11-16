# R4 하네스 판정: 두 경로 묶음 등급 대조 표 (G-1·G-3, 사용자 결정 133 확정 판)

- 작성: control-expert(판정서 작성자), 2026-11-16.
  - 사용자 결정 132: 판정 직전 감사 `scratchpad\r4-source\r4_md2_audit.md`의 권고 G-1·G-3을 이 표로 한다.
  - 사용자 결정 133: 이 판으로 확정한다(436.8 층 묶기 규칙, H-1 대조 범위, H-3·H-4 G-5 처리, 출력 키 결측 처리, H-9 main·H-10 짝 키, H-2 키).
  - 앞 초안(sha `59f1fa5e…5307`)은 이 판으로 대신한다.
- 쓰는 사람: 판정서 작성자와 메인 세션. R4 작성자(경로 1, 2-dyn, 2-terra)에게는 넘기지 않는다.
- 결과 전 고정
  - 이 표는 `judge_932f1fb\`가 생기기 전에 썼다. 하네스 결과 값과 두 경로 출력은 열지 않았다.
  - 키는 M4 `932f1fb`의 두 경로 README·코드(`git show 932f1fb:<파일>`)와 비교기 `--show-map`에서 옮겼다. 실제 출력 꼴은 결과 전이라 확인하지 못했다.
  - **출력 키 결측(결정 133의 4)**: 아래 표의 키가 실제 출력에 없으면 그 묶음은 `판정 불가`이고 멈추고 묻는다. 결과를 본 뒤 다른 키로 바꾸지 않는다.
- 기준 파일

| 대상 | 경로 | sha256 또는 판 |
|---|---|---|
| 경로 1 실행본 | `scratchpad\main\r4run\final\run_judgement_path1_M4.ps1` | 메인 고정 값 |
| 경로 2 실행본 | `scratchpad\main\r4run\final\run_judgement_path2_M4.ps1` | 메인 고정 값 |
| 비교기 파일 | `scratchpad\main\r4run\compare_r4.py` | `8ff3d32ba0aaf5612f007591d03374470327acb3af4e95fc1b967addc155e193` |
| 비교기 열 대응표 | 같은 도구 `--show-map` 마지막 줄 `column_map_sha256` | `5f7ec6faed47e178fbc4566d9d79ec8d3d096d82e19000c94663d6e52e70341a` |
| 경로 1 도구 | `04_scripts/04_hydraulic/coupled/*_4368.py`, `d1_select.py`, `README_judges_4368.md`, `06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py` | M4 `932f1fb` |
| 경로 2 도구 | `…/v5_resume_4368/path2/*`, `…/path2_v5c/*` | M4 `932f1fb` |

- **감사 기록 정정**
  - 판정 직전 감사(`r4_md2_audit.md`)는 "비교기 … 모두 sha `5f7ec6fa`로 결과 전에 고정됐다"고 적었다.
  - `5f7ec6fa…`는 비교기 파일 sha가 아니라 열 대응표(`COLUMN_MAP`·`VALUE_WORDS` 등)의 sha인 `column_map_sha256`이다. 비교기 파일 sha는 `8ff3d32b…`다.
  - 판정서에는 둘을 따로 적는다. 판정 전 대조에서는 비교기 파일 sha로 도구가 같은지 보고, `column_map_sha256`으로 대응표가 같은지 본다.
- 출력 파일 이름(아래 표의 `P1:`·`P2:`)
  - 경로 1: `judge_932f1fb/harness_path1/<이름>`
  - 경로 2: `judge_932f1fb/harness_path2/<이름>`
  - 이름은 두 실행본의 `--out` 값이다. 경로 1 `h2_select.json`은 `d1_judge_4368 --select-out`이 쓰는 파일이다.

## 1. 공통 규칙

### 1.1 등급 낱말 대응표

| 판정서 낱말 | 경로 1에서 읽는 값 | 경로 2에서 읽는 값 |
|---|---|---|
| `통과` | `"통과"` | `"통과"`(`grades_436_8`·`status_4368`), `"pass"`(Findings `status`) |
| `미달` | `"미달"` | `"미달"`, `"fail"` |
| `판정 불가` | `"판정 불가"` | `"판정 불가"`, `"undecidable"` |
| 멈춤(등급 아님, 1.3) | `"멈춤"`, `"stopped"`(u3 `status`), `"멈춤 (G-3 거짓: …)"`(u3 최상위 `status`), `"markers"`(격자 J-P3·J11 `grade`) | `"멈춤"`, `"stop"` |
| `기록 완료` | `"기록 완료"`(`state`). 행은 `"기록"`(`record_state`) | `"기록 완료"`(`status`) |
| `기록 불완전` | `"기록 불완전"` | `"기록 불완전"` |
| (원 규칙 판정이 끝났다는 표시) | u3 `status` `"judged"` | (해당 없음, H-3·H-4 행) |

- 위에 없는 낱말이 나오면 그 묶음은 `판정 불가`이고 멈추고 묻는다. 결과를 본 뒤 대응을 더하지 않는다.

### 1.2 같다고 보는 것

1. 묶음마다 2절의 "등급 값"을 1.1로 옮긴 낱말이 같아야 한다.
2. 묶음마다 멈춤 표지 집합이 같아야 한다. 표지 이름은 RD-4 이름으로 옮겨 비교한다(예: `멈춤 H-7`, `멈춤 H-10`, `S-2`, `S-8`, `S-15`, `H-15`, `G-3 거짓`, `u3 G-5 묻기`).
3. 판정서가 등급을 조합하는 묶음(2절 "조합" 행)은 두 경로 출력에 같은 조합 규칙을 따로 적용해 낸 낱말이 같아야 한다. 판정서는 수를 다시 계산하지 않는다. 출력 값을 읽고, 1.4의 규칙으로 줄을 묶음에 나누는 일만 한다(결정 133의 1).
4. 1~3 가운데 하나라도 다르면 원판 S-13이다. 그 묶음은 `판정 불가`이고, 두 출력을 그대로 적고 묻는다(RD-6, 원판 9.2).

### 1.3 묶음 등급을 정하는 순서

- 멈춤은 등급과 따로 본다(원판 8.2).
  - 멈춤 표지가 하나라도 있으면 그 묶음은 "멈춤, 묻는다"로 적는다.
  - 도구가 낸 등급 낱말이 "멈춤"이면 등급은 "주지 않음"으로 두고, 멈춤 표지 집합만 비교한다.
- 판정 묶음의 등급: `판정 불가` > `미달` > `통과`(원판 8.1, 앞의 것이 이긴다). 묶음 안의 여러 항목·부분 가운데 가장 나쁜 것이 묶음 등급이다.
- 기록 묶음(H-7, IND_LAS, H-12, C-9~C-11; 원판 8.1, rev16 R16-2): `기록 불완전` > `기록 완료`. 등급이 없다.
- 관문(H-11 G-3, J_P 재사용 판독): 참·거짓(재사용 여부)이다. 등급이 없다. 거짓이면 그 귀결대로 한다(H-3·H-4 판정 안 함, J_P 재사용 안 함).
- 436.8 층과 원 규칙 층: 묶음 등급은 두 층의 최악이다.
  - 경로 2 `harness.json`의 `bundles.<묶음>.status`는 436.8 층(4.1·4.2·7.2·9.3·S-15)만 다룬다(`grade_scope`).
  - 경로 1의 436.8 층은 줄 단위 출력을 1.4로 묶는다.

### 1.4 경로 1 436.8 층 줄을 묶음으로 나누는 규칙 (결정 133의 1)

- 대상 출력
  - `record_check.json`의 `stops`(줄 목록)
  - `k1_class.json`의 `stops`와 `class` = 판정 불가 줄(`undecidable` 수의 줄)
  - `r4_inputs.json`의 멈춤·판정 불가 항목
  - `r4_lists.json`의 `bundles.{b}.markers`(이미 묶음별이라 그대로 씀)
- 나누는 열쇠: 각 줄의 결과 파일(저장소 루트 상대 경로, `/` 구분, 블록 RD-7 3 표기)이다. 이 파일을 보충 4-2 표의 "묶음(부분)" 열로 옮긴다.
  - `resume_k1/h1_d1.jsonl` → H-1
  - `las_k1/u3_*.json` → H-3
  - `las_k1/u6_*.json` → H-4
  - `resume_k1/h5_u9_v0.jsonl` → H-5
  - `resume_k1/h6_dg3_v4on.json` → H-6
  - `resume_k1/h7_dg3_off.json` → H-7
  - `resume_k1/h8_*.json` → H-8
  - `resume_k1/h9_stage1.jsonl`, `resume_k1/h9_grid/*`, `resume_k1/h9_grid_v0_sample/*`, `resume_k1/h9_family_F*` → H-9
  - `resume_k1/h10_reuse_rerun.jsonl` → H-10
- 줄에 결과 파일 열이 없거나 위 대응에 없는 파일이면, 그 줄이 든 출력 전체를 판정 불가로 읽는다. 그 출력이 다루는 모든 묶음의 436.8 층은 `판정 불가`이고 멈추고 묻는다(결정 133의 4).
- 한 묶음의 436.8 층 낱말은 다음 순서로 정한다.
  - 그 묶음에 나뉜 줄 가운데 멈춤(`stops`)이 있으면 멈춤 표지
  - 아니고 판정 불가 줄이 있으면 `판정 불가`
  - 둘 다 없으면 `통과`
  - 436.8 층에는 `미달`이 없다. 경로 2 `harness`는 `fail`을 내지 않는다(`932f1fb` `cmd_harness`에 `fail` 호출 없음, 코드 확인). 그런데도 경로 2 `bundles.{b}.status` = `fail`이 나오면 그 묶음은 S-13이다.
- 판정서는 줄을 다시 판정하지 않는다. 출력의 `stops`·판정 불가 표시를 그대로 옮겨 묶음에 넣기만 한다.

## 2. 묶음별 등급 출처

- 형식: `파일: 키`. `{b}`는 묶음 이름이다.
- "등급 값" 열
  - 직접: 도구가 묶음 낱말을 낸다.
  - 조합: 판정서가 같은 규칙으로 두 경로의 항목 값에서 낸다.
  - 한정: 대조 범위를 줄인 것이다.

| 묶음 | 구분 | 경로 1 | 경로 2 | 등급 값과 조합 규칙 |
|---|---|---|---|---|
| H-1 (D-1) | 판정 | P1 `d1_judge.json`: `not_judgeable`(빈 사전 아니면 판정 불가), `errors`(> 0이면 판정 불가), `assumed_boundary`(비어 있지 않으면 묻기 표지), `d1_select.exit_code`(1 = 선별 관문 멈춤, 2 = 입력 결측 → 판정 불가); `r4_lists.json`: `bundles.H-1.markers` | P2 `d1.json`: `stop_codes`, `gates.G-3`(비어 있지 않으면 묻기 표지), `R3-A3.n_ready_undecidable`(> 0이면 판정 불가); `harness.json`: `bundles.H-1.status`·`stop_codes`·`gates` | **한정(결정 133의 2)**. 대조는 멈춤 표지 집합과 판정 불가 여부만 한다. 두 경로 모두 원 규칙(d1 선별)의 묶음 낱말 통과·미달을 내지 않는다. 그래서 통과·미달은 대조하지 않고, 그 사실을 판정서에 공개한다 |
| H-2 (D-1 선별) | 판정(계산) | P1 `h2_select.json`(`d1_select.py` 출력): `exit_code`, `gates.G-1.pass`·`gates.G-3.pass`·`gates.G-4.pass`, `S1.{C2-03,C2-07}.selected`·`.baseline_failure`, `S2.{S-01,S-02}.selected`·`.baseline_failure`·`.fup_rec_excluded`, `S3.rows`·`S3.decision` | P2 `d1.json`: `C2_selected_rows.S1_S2`, `C2_selected_rows.PS-c`, `S1.{C2-03,C2-07}.chosen`·`.baseline_failure`, `S2.{S-01,S-02}.chosen`·`.baseline_failure`·`.fup_rec_excluded`, `S3.rows`, `stop_codes` | 조합(목록 모으기만). 같음 = 다음 넷이 모두 같음. ① 선별 행: P1 `S1.*.selected`와 `S2.*.selected`의 합집합을 코드 포인트 순으로 정렬한 것 = P2 `C2_selected_rows.S1_S2`. ② PS-c 행: P1 `S3.rows` 집합 = P2 `C2_selected_rows.PS-c` 집합. ③ 칸마다(`C2-03`, `C2-07`, `S-01`, `S-02`) `baseline_failure`, 칸 S-01·S-02의 `fup_rec_excluded`. ④ 관문 멈춤: P1 `exit_code` = 1 ↔ P2 `stop_codes`에 G-1·G-3·G-4 가운데 하나 이상. P1 `exit_code` = 2이거나 키가 없으면 판정 불가 |
| H-3 (U-3) | 판정 | P1 `u3_judge.json`: 최상위 `status`(G-3 거짓이면 멈춤 문자열), `u3.<연구>.status`(`judged`/`stopped`/`판정 불가`), `u3.<연구>.gates`, `u3.<연구>.phrase`(기록), `R4.G-5_list_RD7`, `R4.G-6_list_RD7` | P2 `u3.json`: `U-3.status`(pass/fail/undecidable/stop), `U-3.stop_codes`, `U-3.G-5_list.rows`, `U-3.G-6_list.rows`; `harness.json` `bundles.H-3.*` | 조합. 멈춤 = P1 연구 하나라도 `stopped` 또는 최상위 멈춤 / P2 `U-3.status` = stop. **G-5 목록이 비어 있지 않으면 u3 원판대로 멈추고 묻는다**(표지 `u3 G-5 묻기`, 결정 133의 3. `미달`로 읽지 않는다). 판정 불가 = P1 연구 하나라도 `판정 불가` / P2 undecidable. 통과 = 그 밖. P2 `U-3.status` = fail이면서 G-5 목록이 비어 있지 않으면, 같은 "G-5 묻기"로 옮긴다. G-5 목록이 비어 있는데 fail이면 S-13 |
| H-4 (U-6 + IND_LAS) | 판정 + 기록 열 | P1 `u3_judge.json` `u6.<…>.gates`; `ind_las.json`; `r4_lists.json` `bundles.H-4.*` | P2 `u3.json`: `U-6.status`, `U-6.stop_codes`; `harness.json` `bundles.H-4.*` | 조합. 멈춤·판정 불가는 H-3과 같은 규칙이다(G-5는 H-4에 없음). IND_LAS는 기록 열(기록 완료·불완전)이다. P1 `ind_las.json`의 판정 불가·멈춤 표지 키가 없으면 결정 133의 4 |
| H-5 (U-9 V0) | 판정 | P1 `u9_judge.json`: `grade`(멈춤/판정 불가/미달/통과) | P2 `v5j_u9.json`: `status_4368`(통과/미달/판정 불가/멈춤) | 직접 |
| H-6 (dg3 v4_on) | 판정 | P1 `h6_judge.json`: `status`(멈춤 > 판정 불가 > 미달 > 통과, R4-B6) | P2 `p2v5c_noise.json`: `grades_436_8.H-6`; `harness.json` `bundles.H-6.status` | 직접(P2는 두 층의 최악, P1은 1.4로 436.8 층을 더함) |
| H-7 (dg3 끔) | 기록 | P1 `dg3_hash.json`, `keyset_h7.json`, 1.4의 H-7 줄 | P2 `harness.json`: `bundles.H-7.status`·`stop_codes` | 조합. `기록 불완전` = 어느 쪽이든 결측·판정 불가·멈춤 표지 / 아니면 `기록 완료` |
| H-8 (잡음 VB·V0·seedext) | 판정 | P1 `h8_noise_judge.json`: `status`(멈춤/판정 불가/통과; 미달 낱말 없음) | P2 `p2v5c_noise.json`: `grades_436_8.H-8`; `harness.json` `bundles.H-8.status` | 직접. P2 `미달`이 나오면 P1에 미달 낱말이 없으므로 S-13 |
| H-9 (main·pressure_only) | 판정 | P1 `stage1_judge.json`: `findings`, `errors`, `unknown_lines`, `R4.H-9`(J-P3·J11·RD-8·RD-10 블록), `R4.markers` | P2 `p2v5c_stage1.json`: `grades_436_8.H-9_stage1` | P2 직접 / P1 조합: 멈춤 = `R4.markers` 가운데 H-9 표지, 판정 불가 = `R4.H-9`의 RD-8·RD-10 판정 불가 수 > 0 또는 `unknown_lines`·`errors` > 0, 그 밖 = 통과. P1에 짝 키가 없는 경로 2 항목(J 표 실패 낱말, J9, m2_law 등)은 RD-13 K-R 표의 "한 경로 항목"으로 공개하고 묶음 낱말 대조에 넣지 않는다(결정 133의 5) |
| H-9 (격자 768) | 판정 | P1 `stage1_judge.json` `R4.H-9_grid_R16_7`(`grade`: 통과/markers/판정 불가, J-P3·J11만); `grid_h10.json`(`N_raw`, `N_F`, `application_condition`, `h10_marker`, `record.fault`, `record.not_judgeable`, `v0_pair_source.source`) | P2 `p2v5c_grid.json`: `grades_436_8.H-9_grid`(J-P3·J9·J11·m2_law·태그·S-15, 보충 5 FAULT·판정 불가 제외), `grid.supplement6_inputs`, `grid.grid_records` | 조합(보충 6-4 순서). 판정 불가 = 판정 불가 행 ≥ 1 ∨ 짝 출처 판정 불가 ∨ 적용 조건 판정 불가 ∨ J-P3·J11 판정 불가 / 미달 = FAULT ≥ 1 / 멈춤 = `멈춤 H-10` 또는 J-P3·J11 표지. 범위가 다른 직접 낱말(P1 `grade`, P2 `grades_436_8.H-9_grid`)은 서로 비교하지 않는다. P2만 내는 J9·m2_law는 K-R "한 경로 항목"(결정 133의 5) |
| H-9 (계열 𝓕) | 판정 부분 | P1 `family_f.json`: `result`, `R-1`~`R-4`, `k` | P2 `p2v5c_grid.json` `grid.family_F_rule.*` | 직접(비교기 항목). 결과는 보충 5-4 표로 격자 항에 들어간다 |
| H-10 (재실행 하네스) | 판정 | P1 `stage1_judge.json`: `R4.H-10`, `R4.markers`, `U-9_VB_lines.S-15`; `h8_noise_judge.json` `status`의 H-10 멈춤(L2 CP·L1 게이트) | P2 `p2v5c_stage1.json`: `grades_436_8.H-10`; `p2v5c_noise.json`의 H-10 멈춤 | P2 직접 / P1 조합(H-9 main과 같은 규칙. `U-9_VB_lines.S-15`가 거짓이면 S-15 표지). P1 `item8_J`·`13.1`·`overlap_J`의 실패 낱말과 P2 짝이 없는 항목은 K-R "한 경로 항목"(결정 133의 5) |
| H-11 (G-3) | 관문 | P1 `h11.json`: `G-3`, `pass`(= G-3 ∧ 정체성 이상 없음), `false_pairs_RD7` | P2 `g3.json`: `G-3`, `G-3_false_list.rows` | 직접(참거짓). P1 `pass`와 P2 `G-3`가 다르면 S-13 |
| H-12 (T4h 기록) | 기록 | P1 `h12.json`: `state`(기록 완료/불완전), `markers` | 없음(경로 1만, rev16 R16-10 1 (f)) | 한 경로 기록. 대조하지 않고 판정서에 그렇게 적는다 |
| C-9 | 기록 | P1 `x16_records.json`: `bundles.C-9.state`, `bundles.C-9.p18_premise.holds`, `bundles.C-9.controller_commands_same` | P2 `c16.json`: `bundles.C-9.status`, `C-9_P-18.premise`, `C-9_P-18.commands_equal` | 직접(기록 낱말) |
| C-10 | 기록 | P1 `x16_records.json` `bundles.C-10.state` | P2 `c16.json` `bundles.C-10.status` | 직접 |
| C-11 | 기록 | P1 `x16_records.json` `bundles.C-11.state` | P2 `c16.json` `bundles.C-11.status` | 직접 |
| J_P (7.3, RD-11) | 관문 | P1 `jp_reuse.json`: `reuse`, `stop_markers`, `rows` | P2 `jp.json`: `reuse`, `stop_markers`, `rows` | 직접. 멈춤 표지가 있으면 `reuse`는 없다(RD-11 7) |
| 436.8 층(H-1~H-10 공통) | 판정 층 | 1.4 | P2 `harness.json` `bundles.{b}.status`·`stop_codes`·`gates` | 1.4로 묶은 P1 낱말과 P2 `status`를 1.1로 옮겨 대조 |

## 3. 결정 133으로 닫은 것

| 앞 초안의 확인 필요 | 결정 133 | 이 판에 반영한 곳 |
|---|---|---|
| 1. 경로 1 436.8 층 묶음 상태 | 판정서는 두 경로가 낸 줄을 결과 파일 경로로 묶는 일만 한다. 묶는 규칙은 표에 고정한다 | 1.2 3, 1.4 |
| 2. H-1 묶음 낱말 없음 | 멈춤 표지 집합과 판정 불가 여부만 대조한다. 통과·미달 낱말이 없다는 사실은 공개한다 | 2절 H-1 행, 4절 공개 |
| 3. H-3·H-4 G-5 | G-5가 비어 있지 않으면 u3 원판대로 멈추고 묻는다 | 2절 H-3 행, 1.2 2 표지 `u3 G-5 묻기` |
| 4. H-9 main·H-10 짝 키 | K-R의 "한 경로 항목"으로 둔다 | 2절 H-9·H-10 행 |
| 5. H-2 경로 1 키 | 경로 1 README와 코드(M4)에서 확정 | 2절 H-2 행. 근거: `d1_select.py`(`932f1fb`) `select()`가 `gates`·`S1`·`S2`·`S3`·`crawler_x3`를 내고, `select_cell`이 `selected`·`baseline_failure`·`ranking`·`candidates`, `select_soft_slope`가 `fup_rec_excluded`, `s3_selection`이 `profiles`·`rows`·`decision`을 낸다. 최상위 `exit_code`가 있다. 경로 2 `p2_d1.py` `recount`는 같은 칸 이름(`C2-03`, `C2-07`, `S-01`, `S-02`)에 `chosen`을 쓰고 `C2_selected_rows.S1_S2`(합집합 정렬)·`PS-c`를 낸다 |
| 6. 출력 키 결측 | 그 묶음은 판정 불가로 두고 멈춘다. 결과 뒤에 키를 바꾸지 않는다 | 머리말, 1.1 끝, 1.4 |

## 4. 비교기 항목의 귀결 (G-3)

- 비교기(`compare_r4.py`, `field_sources`)는 모든 차이를 종료 1로 묶는다. 판정서는 항목마다 아래 귀결을 따른다.
- "S-13 멈춤": 그 차이로 묶음 등급이나 등급을 바꾸는 목록이 갈린다. 그 묶음은 `판정 불가`이고 묻는다.
- "공개 기록": K-R(정의 차이) 표에 싣고 등급은 그대로 둔다.
- "0 대 ≥1 규칙": 셈 차이 자체는 공개 기록이다. 다만 한 경로가 0이고 다른 경로가 1 이상이면 판정 불가·S-8 여부가 갈리므로 S-13이다.

| 비교기 항목 | 귀결 | 근거 |
|---|---|---|
| `J-P3`, `J11`, `S-6` | S-13 | RD-7 목록(멈춤 H-7·L-e·멈춤 S-6), JD-1·JD-3 |
| `G-5`, `G-6` | S-13 | RD-7 1, JD-2·JD-7. G-5는 H-3 묻기 표지도 정한다 |
| `bundle_markers` | S-13 | 1.2 2 |
| `dg3_substituted` | S-13 | H-8 S-15 대조 수 |
| `g3`, `g3_false_pairs` | S-13 | H-11 관문(거짓이면 H-3·H-4 판정 안 함) |
| `jp_reuse`, `jp_stop_markers`, `jp_rows`, `jp_rows_count` | S-13 | RD-11 재사용 판독 |
| `application`, `family_table` | S-13 | 보충 4-5·6-3 적용 조건 |
| `family_R1`~`family_R4`, `family_k`, `family_result`, `family_R3_violations`, `family_R4_violations` | S-13 | 보충 5-4 표 선택 |
| `grid_raw`, `grid_excluded`, `grid_n_raw`, `grid_n_f`, `h10_marker`, `h10_term`, `h10_value` | S-13 | 보충 5-3·5-4, 6-4 멈춤 H-10 |
| `pair_source`, `sample_jobs`, `sample_same` | S-13 | 보충 6-2 짝 출처 |
| `fault_rows`, `n_fault` | S-13 | 보충 6-4 FAULT ≥ 1 = 미달 |
| `undecidable_rows` | S-13 | 보충 6-4 판정 불가 |
| `pass_to_pass`, `fail_to_pass`, `fail_to_fail` | 공개 기록 | 보충 5-2 "기록" |
| `rd8_record` (H-1·H-3·H-4 RD-8 꼴) | 공개 기록. RD-8 표지 유무가 갈리면 `bundle_markers`로 S-13 | 결정 132 G-3 |
| `rd8_judged` (H-6·H-8·H-9·H-10 J-P3 판정 불가 수) | 공개 기록 + 0 대 ≥1 규칙 | 판정 불가 여부 |
| `rd9`, `rd9_v5c` | 공개 기록 + 0 대 ≥1 규칙 | RD-9 S-8 |
| `rd10` | 공개 기록 + 0 대 ≥1 규칙 | RD-10 판정 불가 |
| `rd13_lists`, `rd13_lists_v5c` | 공개 기록(sha만) | RD-13 "한 경로에만 있어도 멈추지 않음" |
| `c16_bundles`, `c16_rows`, `c16_identity_stops`/`c16_stops`, `c9_premise`, `c9_commands_same`, `c16_items` 29개 | 공개 기록. 값이 다른 C 행은 `기록 불완전`, 그 묶음도 `기록 불완전` | 결정 132 G-3, rev16 R16-2(기록 묶음) |
| (비교하지 않음) 묶음 등급 | 이 표 2절로 판정서가 대조한다. 다르면 S-13 | G-1 |
| (비교하지 않음) H-12 | 경로 1만, 대조 없음 | rev16 R16-10 1 (f) |
| (비교하지 않음) 입력 sha 블록 | G-2 표로 따로 | G-2 |

- 비교기 `missing`
  - J-P3·S-6·G-5·G-6 목록이 비어 있으면(`must_not_be_empty`) JD의 "빈 집합 = 멈춤"이다. 판정서는 멈추고 묻는다.
  - 그 밖의 `missing`(키가 출력에 없음)은 그 묶음 `판정 불가`이고 멈추고 묻는다(결정 133의 4).
- 비교기 종료 1은 실패가 아니다. 위 표로 항목별 귀결을 정한다(감사 N-7과 같은 취지).

## 5. 판정서 공개 항목 (이 표에서 나오는 것)

1. H-1은 두 경로 모두 원 규칙 묶음 낱말(통과·미달)을 내지 않는다. 그래서 대조는 멈춤 표지 집합과 판정 불가 여부로 한정했다(결정 133의 2).
2. 경로 1은 436.8 층 묶음 상태를 내지 않는다. 판정서가 1.4 규칙으로 줄을 결과 파일 경로로 묶었다(결정 133의 1). 판정서가 다시 계산한 값은 없다.
3. H-3 G-5가 비어 있지 않은 경우는 `미달`이 아니라 u3 원판의 "묻기" 멈춤으로 읽었다(결정 133의 3).
4. H-9 main·격자·H-10에서 한 경로에만 있는 항목은 K-R의 "한 경로 항목"으로 두었다(결정 133의 5).
5. 감사 기록의 sha 표기 정정: `5f7ec6fa…`는 `column_map_sha256`, 비교기 파일은 `8ff3d32b…`(머리말).
6. 출력 키 결측 처리는 결과 전에 정했다(결정 133의 4).

## 6. 이 파일의 sha

- 판정서·결정 기록에는 이 파일의 LF 바이트 sha256을 적는다. 값은 메인 보고에 있다.
