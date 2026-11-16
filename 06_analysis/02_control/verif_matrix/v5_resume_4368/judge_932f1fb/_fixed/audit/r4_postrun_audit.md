# 436.8 R4 하네스 판정 후 감사 (verif-protocol-auditor, 2026-11-16)

## 감사 요약
- 대상
  - M4 `932f1fb`
  - 출력: `judge_932f1fb\harness_path1`(목록 `593f1cc2`), `harness_path2`(목록 `cdd31c3d`)
  - 비교기 결과 `compare_r4_result.json`: equal 19, differ 2, missing 0
  - 등급 대조 표 `r4_grade_compare_table.md`(`602618ea`, 결정 133·134)
- 판정: 차단 2 / 권고 4 / 참고 8. 판정서 등급을 확정하기 전에 사용자 결정이 필요한 항목이 있다(확인 필요 Q1~Q6).
- 이번 감사는 PowerShell 도구를 쓸 수 없는 상태에서 했다(자동 분류기 판정 없음이 연속으로 났다). 그래서 Read·Grep으로만 확인했다. 아래 "검사하지 못한 것"에 그 범위를 적었다.

## 발견 사항 (심각도순)

### [차단][E·I] B-1 경로 1의 `stage1_judge`와 `stroke_H-9`가 입력 오류로 끝나 H-9·H-10 경로 1 출력이 없다. 원인은 실행 스크립트의 변수 덮어쓰기다
- 근거
  - `harness_path1\logs\stage1_judge.out.txt`와 `stroke_H-9.out.txt`가 둘 다 `{"exit_code": 2, "error": "grid_r69_top: [Errno 2] No such file or directory: 'grid_r69_top'"}`이다.
  - `harness_path1\sha256_manifest.txt`에 `stage1_judge.json`·`stroke_H-9.json`이 없다.
- 원인(입력 문제이고, 판정 불가 판정이 아니다)
  - 실행본 `run_judgement_path1_M4.ps1` 62~63행이 `$Grid`(격자 결과 파일 4개 경로 배열)를 정의한다.
  - 153행 `foreach ($grid in 'grid_r67_main', …, 'grid_r69_top')`이 같은 변수를 덮어쓴다. PowerShell 변수 이름은 대소문자를 가리지 않는다.
  - 그래서 159행 `stage1_judge … '--grid') + $Grid`와 183행 `stroke_H-9 … + $Grid`에는 마지막 반복값 문자열 `'grid_r69_top'` 하나만 들어갔다.
  - 도구는 스크립트가 넘긴 인자 그대로 실패했고, 도구 결함은 아니다.
- 영향
  - 등급 대조 표 2절에서 H-9(main·격자)와 H-10의 경로 1 출처는 `stage1_judge.json`의 `findings`, `errors`, `unknown_lines`, `R4.H-9`, `R4.H-9_grid_R16_7`, `R4.H-10`, `R4.markers`, `U-9_VB_lines.S-15`다.
  - 이 출처가 없으므로 결정 133의 4(출력 키 결측)에 따라 H-9·H-10은 `판정 불가`이고 멈추고 묻는다.
  - JD-1(J-P3 = JP-base)은 같다. 그래서 결정 51로는 H-9 격자·H-10이 `미달`이 되지만, 원판 8.1에서 `판정 불가`가 `미달`보다 앞선다.
  - 격자 H-10 항(`grid_h10.json`, 보충 5·6)과 J-P3 목록(`r4_lists.json`)은 영향받지 않았다. 둘 다 비교기에서 같았다.
- 감사자 책임: 재감사(`r4_prerun_reaudit.md`)와 MD-2(`r4_md2_audit.md`)에서 이 덮어쓰기를 찾지 못했다. MD-2에서 "경로 1 실행본은 재감사 때 판과 같고 … 그대로"라고만 적었다.
- 권장 조치(사용자 결정 필요, Q1): 결정 132 G-4대로 승인을 받은 뒤 새 폴더에서 두 단계만 다시 돌린다.
  - 폴더: `harness_path1_retry1`
  - `$Grid`는 4개 경로로 고치고, 반복 변수 이름은 바꾼다. 이 수정은 스크립트 diff로 남긴다.
  - 같은 M4, 같은 도구 blob, 같은 입력(G-2 스냅숏 뒤 대조)을 쓴다.
  - 이 재실행은 경로 1 출력을 새로 만드는 일이다. 경로 2 출력과 비교기 결과를 이미 본 뒤이므로, RD-6(본 뒤 수정 금지)과의 관계를 판정서에 공개한다.
  - 도구와 입력이 같아 출력이 정해져 있다는 점이 근거다. 다만 "다시 돌릴지"를 결과 본 뒤에 정한다는 점은 남는다.
  - 대안은 H-9·H-10을 `판정 불가`로 확정하는 것이다.

### [차단][R] B-2 H-3 멈춤 표지 집합이 두 경로에서 다르다(경로 2만 G-1). 등급 대조 표 1.2(2)에 따라 S-13이다
- 근거
  - 경로 2 `u3.json` `U-3.stops`(8436~8439행)에 `{"code": "G-1", "where": "pairs", "why": "V0 / VB key sets differ (134)"}`이 있다. `U-3.stop_codes`는 `["G-1", "G-5", "G-6"]`이다.
  - 경로 1 `u3_judge.json`은 연구별 G-1이 모두 `pass: true`다(326·732·981·1232·1683·2928·3443행 등). 멈춤은 G-5(h9·g6·g8)와 G-6(g8)뿐이다(`findings` 4740~4745행).
- 원인[추정 아님, 코드 확인]
  - 경로 2 `p2_u3.py:204-214` `records_loc`는 screen 꼴 파일(연구 C·D, `results[]`)의 suite를 `r.get("suite") or stem_suite`로 정한다. `stem_suite`는 파일 이름 `u3_C_V0`·`u3_C_VB`라서 V0와 VB 키가 짝지어지지 않는다(C 34 + D 33 = 67 × 2 = 134).
  - 같은 이유로 경로 2는 C·D에서 VB 고유 실패(G-5)를 찾을 수 없다. 이번에는 경로 1 G-5 목록에도 C·D가 없어 JD-2는 같았다.
- 실패 시나리오: 경로 2 도구 결함 때문에 H-3의 멈춤 표지가 하나 더 붙는다. RD-6에 따라 경로 2 도구는 고칠 수 없다.
- 처리: 등급 대조 표 1.2(2)와 4절 `bundle_markers`에 따라 H-3은 S-13 → `판정 불가`이고 묻는다. 어차피 H-3은 S-6과 `u3 G-5 묻기`로 멈추는 묶음이지만, 표지 집합 차이는 판정서에 그대로 적는다(Q2).
  - 덧붙임: 실행본의 `Assert-U3Counts`는 키 수 합(1,114)만 보므로 이 결함을 잡지 못했다.

### [권고][R] A-1 C-9~C-11은 "기록 완료"가 아니라 `기록 불완전`으로 적어야 한다
- 근거: 등급 대조 표 4절 C 행은 "공개 기록. 값이 다른 C 행은 `기록 불완전`, 그 묶음도 `기록 불완전`"이라고 정한다. 결정 132도 "C-9~C-11은 그 행 기록 불완전"이라고 한다.
- 비교기 `item_differences`(`compare_r4_result.json` 665~852행)로 보면 8행 모두 값이 다르다.
  - C-9: `R4368X_G1_B_top_Fs4_V0_gateoff`, `_gateon`(`max_stroke_mm`)
  - C-10: `rigidS1FL`/`FR` × V0/VB 4행(`G6`, `max_stroke_mm`)
  - C-11: `J2_B_top_Fs0_L2_V0`/`VB`(`loc_period_crawler_max_N`, `…_over_W`)
- 따라서 C-9·C-10·C-11 세 묶음 모두 `기록 불완전`이다. 도구가 낸 상태(두 경로 `기록 완료`)는 판정서 낱말이 아니다.
- 메인의 분류("공개 기록, S-13 아님")는 맞다. 다만 "묶음 상태 기록 완료"는 표와 다르다.
- 값 차이의 성격
  - `max_stroke_mm`: 경로 1은 다리별 4개 목록, 경로 2는 최댓값 스칼라다. 경로 2 값이 경로 1 목록의 최댓값과 같다(예: 402.589…, 609.575…, 590.661…). 표기 차이다.
  - `loc_period_crawler_max_N`: 0.014 %(J2 V0 4754.98 대 4755.64), 0.046 %(J2 VB 5081.85 대 5084.17)로, 1e-9 허용을 넘는다. 창이나 표본 정의 차이로 보인다[추정].
  - `G6`: 정의 차이다. 경로 1은 G6-1을 `flag`, VB의 G6-2·G6-7을 `flag`, G6-5를 `해당 없음(rigid_base)`로 낸다. 경로 2는 G6-1을 `pass`, G6-2·G6-7을 `fail`, G6-5를 `not_judgeable`로 낸다. 경로 1은 강등(FLAG)을 적용했고, 경로 2는 보충 2-5대로 P3 값을 그대로 옮겼다.
  - 이 G6 값은 JD-3의 "G-5 g6(`rigid+S1@FL`·`@FR`) 질문" 근거 자료이므로, 두 경로 값을 모두 사용자에게 보여야 한다(Q4).

### [권고][R] A-2 RD-10 H-9 `input_missing` 288 대 204는 범위 차이다. 공개 기록 분류가 맞다
- 근거
  - `undecidable`은 두 경로 모두 0이다(`compare_r4_result.json` 618~627행). 등급 대조 표 4절 `rd10` 규칙("공개 기록 + 0 대 ≥1 규칙")에 걸리지 않는다.
  - 차이 84는 보충 4-2의 V0 표본 run 수 84와 같다. 경로 1 `r4-lists`는 H-9에 V0 표본 4파일을 넣고(README_judges 107행 "H-9에 V0 표본 4파일을 더해"), 경로 2 `path2_v5c`는 V0 표본을 J11 대상으로 읽지 않는다[추정, 수치 일치].
- 판정서 K-R 표에 "경로 1은 V0 표본 84 run 포함"으로 적는다. 독립 재집계는 하지 못했다(도구 제약).

### [권고][R] A-3 H-1 경로 2 `d1.json` `status`가 `undecidable`이다. 등급 대조 표의 H-1 경로 2 키에는 이 값이 없다
- 근거: `d1.json` 1125~1190행. `R3-A2` 재집계 차이 2건이 있다. `D1|H-R-A-S1|rigid+S1@FL|T|flat|K1`의 VB(eps 0.002)와 V0(eps 0) 줄이고, 사유는 "G6-7 should be FLAG P3-8_preloc_loss (U-S9-G6c) in demoted_items, not a failure (S-13)"다.
- 표 H-1 행의 경로 2 키는 `stop_codes`(빈 목록), `gates.G-3`(빈 목록), `R3-A3.n_ready_undecidable`(0), `harness` H-1(pass)이다. 표 글자대로 읽으면 경로 2도 "판정 불가 아님"이고, 경로 1(`not_judgeable` {}, `errors` 0)과 같다.
- 경로 2의 묶음 상태가 `undecidable`인데 표가 이 키를 고르지 않은 것은 결과 전 고정이다. 결정 133은 결과 뒤 키 교체를 금지한다. 그래서 글자대로 읽어 "같음"이 되지만, 판정서에 공개해야 한다(Q3).
- 같은 G6-7 강등 차이가 C-10(A-1)에도 나온다.

### [권고][R] A-4 표 글자를 그대로 적용하기 애매한 출력 키가 셋 있다(결과 전 고정 표의 적용 문제)
1. H-3 경로 1 `u3_judge.json` 최상위 `status`: G-3이 참이면 코드가 이 키를 쓰지 않는다(`u3_judge_4368.py:544-547`은 G-3 거짓일 때만 `status`를 반환). 표 H-3 행은 "최상위 `status`(G-3 거짓이면 멈춤 문자열)"라고 적었다. 괄호 문장으로 보면 "없음 = G-3 거짓 아님"으로 읽힌다. 결정 133의 4(키 결측 = 판정 불가)를 글자대로 적용하면 H-3이 판정 불가가 된다(Q5-a).
2. H-4 경로 1 `ind_las.json`: 표는 "판정 불가·멈춤 표지 키가 없으면 결정 133의 4"라고 한다. 출력 최상위 키는 `record_state`(`"기록"`), `gate_unreadable`(0), `adapter_defect`(false), `not_started_differ`([])이고, `status`·`markers`는 없다(Q5-b).
3. 1.4 경로 1 436.8 층: `k1_class.json` `stops[].file`이 `06_analysis\\03_hydraulic\\…`처럼 역슬래시 경로다. 표 1.4는 "저장소 루트 상대 경로, `/` 구분"으로 묶고, "대응에 없는 파일이면 그 출력 전체 판정 불가"라고 정한다. 구분자만 다르다(Q5-c).
- 세 경우 모두 결과를 본 뒤에 읽는 법을 정하는 셈이다. 사용자 결정으로 닫고 판정서에 공개한다.

## 등급 대조 결과 (등급 대조 표 602618ea 적용)

| 묶음 | 경로 1 | 경로 2 | 대조 | 묶음 귀결(판정서용 초안) |
|---|---|---|---|---|
| H-1 | 표지 없음, 판정 불가 아님(`d1_judge` `not_judgeable` {}, `errors` 0, `assumed_boundary` [], `r4_lists` H-1 markers []) | 표지 없음, 판정 불가 아님(표 키 기준). `d1.status`는 undecidable(A-3) | 같음(한정 대조) | 통과·미달 낱말 없음(결정 133의 2) + A-3 공개 |
| H-2 | 선별 4행 {D1C2_middle/bottom_rollm4.4_Fs4, D1S_J1_B_middle/bottom_Fs4_r0_pm2p8}, PS-c 2행, baseline_failure 모두 false, fup_rec_excluded false, exit 0 | `C2_selected_rows.S1_S2` 같은 4행, PS-c 같은 2행, 칸별 값 같음, stop_codes [] | 같음 | 선별 확정 |
| H-3 | 멈춤: S-6(20줄), G-5(h9·g6·g8), G-6(g8) | 멈춤: S-6, G-5, G-6, **G-1** | **다름(B-2)** | S-13 → 판정 불가, 묻기 |
| H-4 | 표지 없음 | U-6 pass, harness pass | 같음(A-4-2 미결) | 통과(ind_las 키 해석 Q5-b) |
| H-5 | `u9_judge` grade 통과 | `v5j_u9` status_4368 통과 | 같음 | 통과 |
| H-6 | `h6_judge` 통과, 436.8 층 줄 없음 | `grades_436_8.H-6` 통과, harness pass | 같음 | 통과 |
| H-7 | `dg3_hash`·`keyset_h7` exit 0, 436.8 줄 없음 | harness pass | 같음 | 기록 완료 |
| H-8 | `h8_noise_judge` 통과 + 436.8 층 S-6(47줄) | `grades_436_8.H-8` 통과 + harness S-6 | 같음 | 멈춤 S-6, 묻기(JD-3). seedext `L2\|g6\|56\|ref\|J2\|top\|Fs0` "VB 체계적 악화 의심(하네스)"는 두 경로 모두 적었다(경로 1 `findings`, 경로 2 Fisher p 5.3e-6) |
| H-9 main | **출력 없음(B-1)** | `grades_436_8.H-9_stage1` 통과 | 대조 불가 | 판정 불가(키 결측), 묻기 |
| H-9 격자 | `R4.H-9_grid_R16_7` **없음(B-1)**. `r4_lists` 표지 "J-P3 멈춤 H-7", `grid_h10` N_F 0·적용 참·R 통과·FAULT 0 | `grades_436_8.H-9_grid` 멈춤(H-7), 격자 기록 같음 | 표지 같음, 경로 1 등급 출처 없음 | 판정 불가(B-1). B-1이 해소되면 JD-1에 따라 미달 + 멈춤 H-7 |
| H-9 계열 𝓕 | `family_f` pass | `family_F_rule` pass | 같음 | 적용 참, R-1~R-4 통과 → H-10 격자 항은 N_F = 0, 멈춤 H-10 없음 |
| H-10 | `R4.H-10` **없음(B-1)**. `r4_lists` 표지 "J-P3 멈춤 H-7" | `grades_436_8.H-10` 멈춤(H-7) | 표지 같음, 경로 1 등급 출처 없음 | 판정 불가(B-1). B-1이 해소되면 JD-1에 따라 미달 + 멈춤 H-7 |
| H-11 | G-3 참, pass 참 | G-3 참 | 같음 | 관문 참 |
| H-12 | 기록 완료 + 표지 `R17-2a 범위 공백` | (경로 1만) | 대조 없음 | JD-4대로 멈추고 묻기(예정된 멈춤) |
| C-9·C-10·C-11 | 도구 상태 기록 완료 | 도구 상태 기록 완료 | 행 값 다름(A-1) | **기록 불완전**(표 4절) |
| J_P | reuse 참, 멈춤 표지 없음 | reuse 참 | 같음 | 재사용 |

## JD 비교 결과 (비교기 결과 그대로, 귀결은 등급 대조 표 4절)
- JD-1 J-P3 = JP-base: 두 경로 모두 같음, 5줄.
  - 독립 재집계(Grep)로 확인했다: `h10_reuse_rerun.jsonl` 28·172·245행이 RR 2·3·4이고, `grid_r67_top.json`에 FR 3, `grid_r69_bottom.json`에 RR 2가 있다. 다리 {FR, RR×4}가 기준 집합과 같다.
  - 귀결: 결정 51의 미달. 단 B-1 때문에 H-9·H-10은 판정 불가가 앞선다.
- JD-3 S-6 = S6-base: 67줄 같음. 귀결: C-9·C-10 기록 뒤 사용자 질문(JD-3). C 기록이 기록 불완전(A-1)이므로 질문할 때 두 경로 값을 함께 보인다(Q4).
- JD-2 G-5 = 5키: 같음. 귀결: R16-15 1 처리(한계 기록 3, 확인 중 2). 표 H-3 행에 따라 `u3 G-5 묻기`.
- JD-7 G-6 = 3키: 같음. 귀결: R16-15 4(H-12로 닫음). 다만 H-12는 R17-2a 멈춤이다(JD-4).
- JD-8 RD-8 표지: H-1·H-3·H-4 모두 두 경로에서 없음.
- RD-11: 12행, 멈춤 표지 없음, 재사용 참으로 같음.
- 보충 5·6: 짝 출처 저장(8/8), N_raw 2, N_F 0, 적용 조건 참, 𝓕 R-1~R-4 통과, FAULT 0, 판정 불가 행 0, 멈춤 H-10 없음. 모두 같음.

## 멈춤 표지 모음
- 멈춤 H-7(J-P3): H-9 격자, H-10. 두 경로 모두 있다.
- 멈춤 S-6: H-3, H-8. 두 경로 모두 있다.
- u3 G-5 묻기: H-3.
- G-6: H-3 g8 3키.
- G-1(경로 2만, B-2): H-3.
- 멈춤 H-10: 없음.
- R17-2a 범위 공백: H-12(JD-4).
- 사용자 확인 문구: H-8 seedext `L2|g6|56|ref|J2|top|Fs0` "VB 체계적 악화 의심(하네스)". 두 경로 모두 있다(결정 49의 그 키).

## 축별 점검
- (S) 봉인
  - 경로 2 `seal.json`에 `false` 값이 없다.
  - 경로 1 `r4_lists.json` `rules_seal`의 각 판(표본 6판)에서 `expected` = `seal_file` = `rules_file`이다.
  - 경로 2 실행본 `Assert-StepOutput`이 S-1을 치명으로 보는데, rc 표는 모두 expected다(`harness_path2\logs\rc_gate.tsv`).
- (I) 실행 정체성
  - 경로 1 `head_check.json`: head = expected = `932f1fb…`, blob 14개 `same: true`, `src_params_changed` [].
  - 경로 2 `u3.json` 등의 `head_check.ok`는 true다(실행본 단언 통과).
  - `sidecars.json`: `files` 20, `records_start` = `records_end` = 24, `problems` [], `expected_head` R2.
  - 입력 스냅숏 3,608개 "변경 0"은 메인 보고를 따랐다. 독립 대조는 하지 못했다.
- (R) 규칙과 도구: B-1(스크립트), B-2(경로 2 키 결함), A-3·A-4(표 적용).
- (C) 재집계
  - JD-1 J-P3 5줄과 다리: Grep으로 원 결과에서 다시 세어 같았다.
  - RD-9 수(H-1 434, H-3 1,114, H-4 242, H-6 135, H-8 1,553 = 1,503 + 50, H-9 768, H-10 426)는 보충 4-2 구조 수와 같다.
  - RD-10 288/204의 독립 재집계는 하지 못했다.
- (E) 빈 통과
  - J11 목록은 두 경로 모두 0줄이고 RD-10 undecidable도 0이다. 빈 목록이 허용되는 항목이지만, 멈춤 설정 줄의 `n_late`를 독립으로 보지는 못했다.
  - G-5·G-6·J-P3·S-6 목록은 비지 않았다.

## 확인 필요 (사용자에게 물을 것)
- Q1(B-1): 경로 1 `stage1_judge`·`stroke_H-9`를 `$Grid`를 고쳐 새 폴더(`harness_path1_retry1`)에서 다시 돌릴까?
  - 같은 M4, 같은 도구, 같은 입력이다. 결과 본 뒤 재실행이므로 공개한다.
  - 아니면 H-9·H-10을 판정 불가로 확정할까?
- Q2(B-2): H-3 S-13(경로 2만 G-1, 경로 2 screen 파일 키 결함)을 판정 불가로 적고, 원인을 공개하는 것으로 둘까? H-3은 원래도 S-6·G-5 묻기로 멈추는 묶음이다.
- Q3(A-3): H-1에서 경로 2 `d1.status` = undecidable(R3-A2 재집계 차이 2건)을 표 글자대로 대조에서 빼고 공개만 할까?
- Q4(A-1, JD-3): C-10 G6 두 경로 값(경로 1 FLAG 강등 적용, 경로 2 미적용)을 함께 보이고 S-6·G-5 g6 질문을 할까? C-9~C-11은 기록 불완전으로 적는다.
- Q5(A-4): 표 글자 적용이 애매한 세 키를 어떻게 읽을까?
  - (a) u3 최상위 `status` 부재 = G-3 거짓 아님으로 읽을지
  - (b) `ind_las.json`의 `gate_unreadable`·`adapter_defect`를 판정 불가·멈춤 키로 읽을지
  - (c) `k1_class` 역슬래시 경로를 `/`로 같게 볼지
- Q6: H-8 seedext "VB 체계적 악화 의심"(두 경로 같음)을 결정 49의 Chrono 확인과 함께 판정서 한계 절로 보낼까?

## 메인 세션 권고
- Q1~Q6을 사용자에게 묻는다. Q1을 승인받으면 재실행 스크립트 diff와 sha, 실행 전후 입력 대조를 남기고 판정 후 재감사를 부른다.
- 판정서에 다음을 공개한다.
  - 감사자가 실행 전·MD-2 감사에서 B-1을 놓쳤다는 사실
  - 경로 1 rc 2 두 단계의 원인
  - G-1 결함

## 위임 필요
- 다음 개정·다음 판정용으로 경로 2(2-dyn) 작성자에게 넘길 결함 메모: `p2_u3.records_loc`가 screen 파일 suite를 파일 이름으로 정한다. 이번 판정에는 RD-6 때문에 적용할 수 없다.
- python-expert에게(`tools/verif` 후보): PowerShell 스크립트 정적 검사 도구. 앞에서 정의한 변수와 대소문자만 다른 `foreach` 반복 변수, Tee+return 꼴을 찾는다.

## 검사하지 못한 것
- PowerShell 도구를 쓸 수 없어서 하지 못한 것: Python 재집계(RD-10 288/204, J11 빈 목록, 격자 N_raw 독립 재계산), 입력 스냅숏 `inputs_before/after.json` 독립 대조, 출력 파일 sha와 목록 대조, `source_guard` snapshot/verify.
- `inputs_before.json`(749a09c3)·`inputs_after.json`(ea76581f)의 내용 대조.

## 실행한 검증
- 도구: Read·Grep만 썼다(출력 JSON·로그·rc 표·sha 목록·비교기 결과·등급 대조 표·결정 132~135).
- 이번 감사용으로 scratchpad `audit-r4-post\grades.py`·`recount.py`를 썼지만 실행하지 못했다. 지우지도 못했다(셸 도구 사용 불가). 메인이 지우거나, 다음 감사 때 지운다.
- 원본 불변: 확인하지 못함(source_guard를 실행하지 못했다). 이 감사의 쓰기는 이 보고서, 위 두 스크립트 파일, 감사자 메모리뿐이다. Read·Grep은 원본을 바꾸지 않는다.
- 사용한 스킬: 없음
