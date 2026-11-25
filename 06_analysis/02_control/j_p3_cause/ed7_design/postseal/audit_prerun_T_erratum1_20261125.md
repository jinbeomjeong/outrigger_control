저장 필요: C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\postseal\audit_prerun_T_erratum1_20261125.md(원문 그대로, 파일 이름은 메인이 정해도 됨)

## 감사 요약
- 본 결과: 판 7 실행 결과는 없다(`j9_runs\8a2a52ce` 없음, `prelaunch_j9\ed7_run_config.json` 없음). 연 것은 키 파일의 필드 이름과 건수(`sens_keys_ed7.json`의 설정별 줄 수, judged·head_only·probe_seen 건수, `expected_j_p3_judged_rows` 값), suite 판정 json(시험 건수·기존 실패 목록), `h8_noise_VB.json`의 L2 사례 키 167개(이름만, 값 없음)다. probe jsonl·V0 main.jsonl·고정 표는 해시만 쟀고 열지 않았다.
- 시점: 실행 전. 판 7 판정 커밋 T의 감사(P7-11), 본 실행 전 감사, 정오 1 봉인 전 감사를 함께 했다.
- 기준 문서
  - 봉인 명세 `jp3_remedy_spec_v7.md`: 10902ffd, `.sha256`과 raw가 같다. LF, BOM 없음, `-text`.
  - 정오 1 초안: cd05e1ea(미봉인, LF, BOM 없음).
  - 실행 커밋 C: 8a2a52ce. 판정 커밋 T: c91065b7(부모 C).
- 판정: **차단 3 / 실행 전 수정 6 / 기록 14**
  - **P7-11은 통과하지 못했다.** T의 범위와 시험은 맞지만, 감사에서 차단 3건이 나왔다. T를 고친 새 커밋 T′(C의 자식)를 만들고 P7-11과 감사를 다시 해야 판정 단계로 갈 수 있다.
  - C로 줄을 돌리는 1~11단계는 명세 4절 5a에 따라 규칙상 막히지 않는다. 다만 정오 1 봉인과 T′ 재작업은 실행을 시작하기 전에 끝내기를 권고한다(M-6).

## 실측 결과(볼 것 1)
| 관문 | 결과 | 근거 |
|---|---|---|
| P7-10 (C 범위) | **통과** | `git diff --name-status b46bdf8f 8a2a52ce` 18경로, 모두 5.1의 (i)~(iv) 안이다. `03_src` diff는 `extend_start_bound.py` 한 덩어리(197~201행, `JP3_SPEC_EDITION_V7 = "10902ffd"`와 docstring)뿐이다. run_v5 diff는 `ED7_KEY_FILE_SHA256` 두 값과 docstring뿐이다. C의 부모는 b46bdf8f, `C:03_src`는 0cffdbdf. ed7-impl은 clean이고, C가 바꾼 18파일의 mtime은 모두 커밋 시각(16:33:24) 이전이다(0/18) |
| P7-4 (C suite) | **통과** | `junit_skips`: 8695 / 통과 8678 / 실패 2 / 건너뜀 15. 실패·건너뜀은 모두 기준 목록 `571f42a1…`에 있다(`suite_judgement.json` 1e020f05, findings 모두 빈 목록). `--critical 'test_ed7_\|test_ed6_harness\|test_extend_start_bound'`로 critical_skipped 0. junit sha b64b7f2b는 판정 입력과 같다. `suite_record.head` = C. SUMS ae9839ca는 sums 불일치 0 |
| P7-11 범위 | **맞음** | T의 C 대비 diff 9경로가 모두 `04_scripts/`·`05_tests/` 아래다. `C:03_src` = `T:03_src` = 0cffdbdf. 실행 경로 목록 155파일의 blob이 C·T 양쪽에서 목록 값과 같다(불일치 0). 목록의 `run_commit` = C, T 안의 목록 blob a3491352는 근거 사본과 같다(sha256 e9c852e4…). 독립으로 넓게 잡은 import 닫힘(04_scripts 257파일, 문자열 이름까지 포함)에도 T가 바꾼 9파일은 하나도 없다 |
| P7-11 시험 | **맞음** | T junit 2650 통과, 실패·건너뜀·xfail 0. 시작·끝 HEAD = T, clean. 바뀐 판정 모듈을 import하는 시험 4개(`test_ed7_judge/adoption/harness/units`)가 모두 84파일 범위에 들어 있다 |
| P7-11 감사 | **차단 3** | 아래 B-1~B-3 |

## 발견 사항(심각도순)

### [차단][R·E] B-1 sens: J-P3를 10설정 전체로 세는데, 기대 행 수는 판정 4설정 값이다 → 결과와 무관하게 `setting_defect`
- 근거
  - 도구: `jp3_ed7_judge.py:886` `jp3 = jp3_of_rows([row for _, row in pairs], folders)`는 460줄 전체(기록 6설정 포함)를 센다. `:888` `jp3_basis(jp3, document["expected_j_p3_judged_rows"])`가 이것을 기대값과 비교한다.
  - 기대값: 봉인 키 파일 `sens_keys_ed7.json`(be930b75)의 `expected_j_p3_judged_rows`는 **104**다. 생성 코드 `ed7_key_lists.py:152`가 `judged` 줄(판정 4설정)만 센다. 실측으로 judged·비head-only 104줄, 전체 비head-only 260줄이다(설정당 46줄, head-only 20).
  - 기록 6설정도 ③ 켬이다: `run_v5.py:269` `VBM{key}` = `_ED7_CONTROLLER`(`_P3X`, 233행). `jp3_j9main_judge.py:275-299`와 `j_p3_inputs.py:143-151`은 설정으로 거르지 않는다.
  - 같은 함수 안에서도 ③ rev 7 조건은 판정 4설정만 본다(`:883,:887`). 두 판정의 범위가 서로 다르다.
- 실패 시나리오
  - 기대 행 수가 맞지 않아(260 ≠ 104) "J-P3 judged rows 260 != 104"가 나오고 감도 단계가 판정 불가로 끝난다. 판 7은 합격할 수 없다.
  - 그와 별도로, 기록 설정 줄의 J-P3 H-7이 감도 실패로 세어진다. 명세 6.2(678행) "기록 설정의 실패는 공개하지만 판정 상태를 바꾸지 않는다"와 어긋난다.
  - e2e 시험(`test_ed7_judge.py:595-645`)은 VBMslow 10줄만 쓰고 기대값을 그 줄로 다시 만들어서 이 결함을 덮지 못했다.
- 확인 범위: 코드와 키 파일로 추적한 결론이다. 도구를 실행해 확인하지는 않았다.
- 권장 조치(python-expert, T′): sens J-P3 판정 집합을 `line["judged"]` 줄로 한정하고, 기록 설정의 J-P3는 기록으로 돌린다. 460줄 배치 꼴(기록 설정 포함)의 합성 시험을 더한다. 규칙 해석이 다르면(기록 설정 J-P3도 판정으로 본다면) 정오에서 기대값 출처를 정한다(control-expert).

### [차단][R·E] B-2 T-JR-12a·12b에 ③ rev 7 조건 판정이 없다
- 근거
  - 명세 6.1(658행): "J-P3: … ③ rev 7을 쓴다 … 판정 설정(VBM 계열)의 행 수는 판정 때 T4h로 센다. 0이면 판정 불가". 6.5(773행)도 같다.
  - 정오 1-13(134~136행)은 "J-P3 판정 행이 적은 12a" 하위 명령에서 조건 읽기가 0이면 판정 불가가 된다고 적었다. 12a가 조건을 계산한다고 전제한 문장이다.
  - 그러나 `condition_judgement` 호출은 `jp3_ed7_judge.py`의 j9main·sens·confirm·cases(664·887·1095·1189행)뿐이다. `jp3_tjr_judge_ed7.py`는 정체성만 대조한다(51-76). `jp3_12b_judge_ed7.py` 전체와 `jp3_12b_judge.py:710-715`(`j_p3_judgement_rev5`)에는 조건 읽기가 없다. T 보고 항목 3도 12a·12b를 들지 않는다.
- 실패 시나리오
  - 12a의 VBM J-P3 판정 줄이나 12b의 VBKM 판정 줄에서 ③ rev 7 조건 침범이 나도 도구가 보지 않는다. 판정 항목 하나가 계산되지 않은 채 통과로 읽힌다.
  - 반대로 정오 1-13 문면대로 봉인하면, 판정서가 도구와 다른 문장을 인용하게 된다.
- 권장 조치
  - 결과를 보기 전에 범위를 정한다(확인 필요 Q-1). 하나는 T′에서 12a t12 새 쪽과 12b judge 판정 줄에 조건 읽기를 더하는 것이다. 이 경우 0이면 판정 불가로 둔다. r79 T4h에 `jp3_t_s`·`jp3_class` 등 `T4H_ARRAYS`가 실제로 있는지는 첫 l1ref·dg3 출력에서 `key_presence --npz-dir`로 본다.
  - 다른 하나는 정오에서 "12a·12b J-P3 = 판 6 꼴, 조건 행 없음"으로 정하고 공개하는 것이다. 이 경우 1-13의 12a 문장도 고친다.

### [차단][I·R] B-3 정오 1-8·1-9의 조건을 T가 구현하지 않았다: T8과 L1 기준 줄의 6.1 정체성
- 근거
  - 1-8(106~108행): "T8 판정 report에 VBM0 줄의 실제 태그를 기록한다. 기대와 다르면 `setting_defect`". 그러나 `judge_t8`(`jp3_ed7_judge.py:1130-1173`)은 `identity_defects`를 부르지 않고 태그도 기록하지 않는다. VBM·VBM0 양쪽 모두 정체성 대조가 없다.
  - 1-9 조건 1·3(113~116행): "6.1 정체성 항목을 r79 줄마다 … 전부 대조", "l1ref 판정 때 출처별로 읽은 값을 report에 기록". 그러나 T에는 l1ref 판정이 없다. L1 기준 4개(`L1_VBM0/L1_VBM/L1a_VBM0/L1a_VBM`) 줄은 어느 하위 명령에서도 6.1 정체성을 대조하지 않는다. `r79_identity_view`는 12b VBKM0·VBKM(`jp3_12b_judge_ed7.py:74-88,178-191`)와 12a t12 양쪽(`jp3_tjr_judge_ed7.py:51-76`)에만 쓰이고, 출처(행·meta)별 값은 남기지 않는다.
- 실패 시나리오: T8 줄이나 L1 기준 줄의 구성 요소·`lsb_settings`·`probe_d6_settings`가 의도와 달라도 드러나지 않는다. 그러면 P7-1 해시 비교와 12a·12b 등급 기준이 다른 구성 위에서 판정된다. 정오 1을 지금 문면대로 봉인하면 도구가 그 조건을 지킬 수 없다.
- 권장 조치(python-expert T′ 또는 control-expert 정오 문면, 봉인 전): T8에 6.1 정체성 대조와 VBM0 실제 태그 기록을 넣고, L1 기준 줄의 정체성 대조와 출처별 값 기록을 dg3-judge·grade-judge(또는 따로 둔 l1ref 하위 명령)에 넣는다. T′을 만들지 않으면 정오 1-8·1-9를 실제 구현 위치에 맞게 고친다.

### [실행 전 수정][R] M-1 probe-repro의 해시 불일치를 "실패"로 분류한다(6.1·P7-9는 `setting_defect`)
- 근거
  - `jp3_ed7_judge.py:1331`이 `failures`에 `_probe_hash_match`의 결과를 넣는다(1364행 "commands_sha256 differs"). 시험 `test_ed7_judge.py:500`이 이 동작을 고정한다.
  - 명세 P7-9(609행)는 "봉인 뒤: 재현 불일치(양방향)면 멈춤, `setting_defect`", 6.1(672행)은 "불일치면 … 상태는 setting_defect"다.
  - 같은 도구의 sens·confirm은 `commands_sha256` 차이를 `setting_defect`로 둔다(832·1022행). 하위 명령 사이에서 분류가 갈린다.
- 실패 시나리오: 같은 재현 불일치가 probe-repro에서는 종료 1(판정 실패, 재실행 거부 계열)로 끝난다. 명세가 뜻하는 "도구·구현 결함 → 사용자에게 묻기" 경로와 다르다.
- 권장: 고정 표 64행 범위의 해시 차이는 `setting_defect`로 두거나, 정오에서 P7-3(114행 전체 해시)과 P7-9를 나눠 정한다(확인 필요 Q-2).

### [실행 전 수정][R] M-2 정오 1-7의 "메인 세션 권고(기록, 관문 아님)"가 "다르면 판정 전에 멈춘다"와 모순되고, 실행 조건이 없다
- 근거: 103행.
- 위험
  - 기록이라면서 판정을 막는 조건이 붙어 있다(기록 단계가 판정을 막는 꼴).
  - 33줄을 C worktree에서 run steps 밖으로 돌리면 worktree에 미추적 파일이 생길 수 있다. 실행 단계 사이에 돌리면 정체성 검사와 겹친다.
- 권장: 관문인지 아닌지 하나로 정한다. 출력 경로는 C worktree 밖이자 `j9_runs\8a2a52ce` 밖으로 하고, 언제 돌릴지(실행 단계와 겹치지 않게, 어느 판정 전인지)를 적는다.

### [실행 전 수정][E] M-3 정오 1-2 조건 1의 `git diff --quiet -- <두 경로>`는 작업본과 index만 비교한다
- 근거: 61행.
- 권장: `git diff --quiet HEAD -- <경로>`나 `git hash-object` 대 `git rev-parse HEAD:<경로>`로 바꾸고, 시점을 "10번째 단계 바로 전"으로 못박는다.
- 이번 감사 시점의 값: sha fa538512 / e5d1d52e, `hash-object` = `HEAD` blob(f9332882 / d323c25d), `diff --quiet HEAD` 0, git 추적됨(c2357844). 실행 직전 값을 대신하지 않는다.

### [실행 전 수정][T] M-4 판정서에 옮길 공개 항목이 한 목록에 모여 있지 않다
- 근거: "판정서에 옮김"이 명시된 것은 1-4(77행)와 1-15(145행)뿐이다. 다음은 "공개"라고만 적혀 있다.
  - 1-2 조건 3(판 6 방식과의 차이)
  - 1-6(T 구현을 보고 범위를 정함)
  - 1-7(봉인 문면 P7-2 "A~F·X11"을 봉인 뒤 결과 전에 E·F 10줄로 좁힘, 판 6과의 실행 차이)
  - 1-13(12a 위험)
- 권장: 정오 끝에 "판정서에 옮길 것" 목록을 하나 두고, P7-2 문면을 좁힌 일도 공개 항목으로 넣는다. 그래야 판정 후 `judgement_checklist`가 이 항목들을 잡는다.

### [실행 전 수정][I] M-5 판정 `--out` 위치에 따라 1-10 SUMS와 T의 `is_clean`이 오염된다
- 근거
  - `code_identity`(`jp3_ed7_judge.py:247-261`)는 `git status --porcelain`(미추적 포함)으로 clean을 판정한다. `--out`이 T worktree 안이면 그 뒤 report의 `is_clean`이 거짓이 된다.
  - 1-10은 단계 폴더에 SUMS를 만든 뒤 판정하라고 한다. 판정 report를 그 단계 폴더의 `judge\`에 쓰면, 판정 후 `sums` 대조에서 목록 밖 파일 경고(종료 1)가 난다.
- 권장: 판정 출력은 T worktree 밖이자 단계 폴더 밖에 둔다(예: `j9_runs\8a2a52ce\judge_<T8>\`). 아니면 정오에 `--allow-extra judge/*`를 적는다.

### [실행 전 수정][T] M-6 T′ 재작업은 실행 출력이 생기기 전에 끝낸다
- 근거: B-1~B-3은 T′을 요구한다. C 실행(1~11단계)은 T 전에도 돌 수 있지만, 출력이 있는 동안 판정 도구를 고치면 "결과가 있는 상태에서 도구를 고쳤다"는 문제가 생긴다.
- 권장: T′과 재감사를 실행 시작 전에 끝낸다. 동시에 해야 한다면 T′ 작성자의 지시문에 `j9_runs\8a2a52ce` 전체를 블라인드 경로로 넣고 공개한다.

### [기록]
1. R-1: `--run-commit`이 CLI로 바뀔 수 있다(`jp3_ed7_judge.py:1393`, 기본값 C). 판정 report의 `inputs.rows.run_commit` = C인지는 판정 후 감사에서 대조한다.
2. R-2
   - C의 `suite_record.json`에는 `head`만 있고 `is_clean`이 없다(T 쪽에는 있다).
   - `jp3_ed6_suite` 핵심 패턴에 `test_ed7_*`가 없다. 다만 이번 실측에서 ed7 시험은 실패·건너뜀 0이다(critical_skipped 0).
3. R-3
   - 목록 json의 `closure_python_files_outside_03_src`는 138인데 T 보고는 "137개 + …"라고 적었다(문면 차이).
   - 정오 1-5 표는 목록 sha를 인용하지 않는다(명세 5.2 "sha 고정"). 값은 `e9c852e41a4691d1ef2ed1f6fa4b581aeded018d8293405910bae4f0ae927901`이다.
4. R-4: `log_errors`(C 건식 로그 14개)는 종료 0이지만 근거가 비어 있다. 건식이라 `errors N` 줄이 0개다. 14개 로그 모두 DONE이나 기대한 STOP(거부 시험)으로 끝났다.
5. R-5: 정체성 관문에 쓰는 외부 도구(`tools\verif\baseline_check.py`, `cpu-scheduler\record.py`·`sample.py`)는 버전이 고정돼 있지 않다. 실행 시작 때 sha를 기록하기를 권고한다.
6. R-6
   - V0 `main.jsonl`과 probe jsonl은 `.git/info/exclude`(23·107행)로 git에서 빠져 있고 sha로만 고정된다(이어받은 상태).
   - 새 T4h `*.npz`는 `.gitignore:41`에 걸린다. 그래서 실행 출력은 로컬 사본과 1-10 SUMS로만 보존된다.
7. R-7: 1-6 문면은 "확인 단계 J7"에 새 비교를 쓴다고 한다. 그러나 T의 confirm은 J7 집합 비교 없이 `event_output.pass`와 Q7-C4 retract WARN만 본다(고정 표 `_d_v0_comparison`과 같음). 문면만 정리하면 된다.
8. R-8: 1-1 근거 (4)의 "T와 감사 전에는 모두 판정 불가"는 메인이 10a 전에 2~9단계를 판정하면 맞지 않는다. 결론(seed는 키 존재로만 정해짐)은 그대로 성립한다. 판정 순서를 적거나 근거를 값 독립성 하나로 줄인다.
9. R-9 [추정]: `unit_verdicts`(`:569-570`)는 항목이 하나도 없는 단위를 통과로 둔다(gate_scan `missing_key_default_pass`). 436.8 이래의 "실패 목록" 설계이고 고정 표도 같은 방식으로 계산했으므로 새 결함은 아닌 것으로 본다.
10. R-10: `ed7_identity_problems`(`:355-367`)는 ③ 켬 줄에 ③ 기록이 아예 없어도 문제로 잡지 않는다. j9main·sens·G1·cases는 행 수 대조로 간접적으로 잡지만 t8은 잡지 못한다(B-3과 함께 처리).
11. R-11: 12a·12b 래퍼의 단계 소속 검사는 `--vbk0-t4h`·`--new-t4h`·`--base-t4h` 폴더를 보지 않는다.
12. R-12: 근거 폴더 `run_commit_8a2a52ce`·`suite_8a2a52ce`·`judge_commit_c91065b7`·`postseal`은 아직 커밋되지 않았다. ignore에 걸리지는 않는다. `postseal`에는 SUMS가 없다. 정오 봉인 때 함께 커밋하고 SUMS를 만든다.
13. R-13(내 절차 위반): Bash에서 파이프를 1회 썼다(`git … status --porcelain | head -5`). 정상 종료했고 Suspended는 없었다.
14. R-14(공개): `ref_check`(spec, `--exclude` 블라인드 3개와 `.claude`)가 비슷한 이름 후보로 `cdry_a1/VBK0_c93.json`을 출력했다. 블라인드 정의(`VBK_c92*`·`VBK_c93*`·`logs/`) 밖의 이름이다. 블라인드 경로는 Read·Grep·Glob하지 않았다.

### 문제 없음을 확인한 것(E·I)
- **조건 읽기 0**: `summarize`(`jp3_rev7_condition.py:244-258`)는 판정 줄의 읽기 합이 0이면 `not_judgeable`이고, `condition_basis`가 이를 판정 불가로 넘긴다. gate_scan `empty_selection_sum_pass`는 오탐이다.
- **키 결측**
  - confirm: `grid_key_problems`가 FAULT를 읽기 전에 판정 불가로 멈춘다(1035행).
  - D 줄: `fault_reasons`가 None이면 재현 차이로 잡힌다.
  - j9main·cases·t8: 줄 집합이 같은지 대조한다.
  - sens: `matched_lines`로 키 줄과 결과 줄을 1:1로 맞춘다.
- **`.done` 결측**: `--step-done`이 없으면 판정 불가, 파일이 없거나 exit·commit·끝 정체성·폴더 소속이 틀리면 `setting_defect`다. 12a·12b 래퍼도 같다.
- **기록 설정 `probe_seen`**: `sens_units`가 기록 설정 줄을 role `record`로 두고, `fixed_table_scope`는 판정 4설정만 쓴다.
- **U832**: `counted_for_k` 거짓 줄은 k에서 빠지고 FAULT·J-P3는 171줄 전체에 건다. `counted_for_k`가 "U832가 아님"과 다르면 `setting_defect`(1101-1104행).
- **재현 대조 순서**: sens·confirm은 재현 대조를 집계보다 먼저 하고 양방향(`reproduction_differences`, 한쪽에만 있는 줄도 차이)으로 본다.
- **상태 순서**: 실패 > `setting_defect` > 판정 불가 > 통과(268-276행).
- **run steps**
  - 단계마다 새 시도 폴더를 쓰고 `Assert-NewOutput`으로 출력 경로를 확인한다. `.done`이 있으면 거부한다.
  - 시작·끝 정체성(HEAD·clean·03_src tree)이 다르면 종료 3이고 `.done`을 남기지 않는다.
  - core kind는 P/E/mixed로 나누고, 잘못된 마스크는 종료 3이다.
  - 입력 sha를 단언한다: 명세, G1·sens 키, L1 키 2종, `Assert-FixedInputs`. 정오 1-2 표의 실행 단계 항목과 같다.
  - D 키 blob 내용의 sha256 = a995abff를 직접 계산해 확인했다(seal_check의 미해결 1건은 오탐).
- **12b seed 충돌**: C·T·메인 `05_tests`의 문자열 키 리터럴이 L2 사례 167개 × seed 50~53(60~83까지)와 겹치는 것은 0건이다. 시험 파일 때문에 seed가 밀리는 일은 없다. 06_analysis 스캔은 블라인드라 미리 돌리지 않았다.

## 규칙↔도구 대조표(5.2 항목, 6.1~6.4, 정오 1)
| 규칙 | 도구 위치 | 판단 |
|---|---|---|
| 5.2-1 J7 새 비교(V0 표, LS 대 VB 표, sens, probe-repro) | `replace_j7` 499-514, 658-659, 546 | 맞음(1-6) |
| 5.2-2 교착 서명(기록) | `line_records` 477-495 | 맞음 |
| 5.2-3 ③ rev 7 판정 키 | j9main·sens·confirm·cases | **12a·12b 없음(B-2)** |
| 5.2-4 키 목록 대조 | `sealed_key_document` 741-752, `matched_lines` | 맞음 |
| 5.2-5 `run_id` int | `rules.grid_run_index` | 맞음 |
| 5.2-6 고정 표 합산·양방향 | `sens_outcome` 826-857, `d_line_differences`, `g1_outcome` | 맞음 |
| 5.2-7 본 단위 = 판정 4설정 ∧ probe_seen | `sens_units` 860-876 | 맞음 |
| 5.2-8 조건 도구 code_identity | `jp3_rev7_condition.py:301-` | 맞음 |
| 5.2-10 k=4 4설정 합산, U832 기록 표 | `cluster_judgement_with_fixed`, `g1_outcome` | 맞음 |
| 5.2-11 판 7 설정 이름 | j9main·t8·cases·hash-match·probe-repro·sens·confirm·12a·12b | 이름 대응은 맞음 |
| 6.1 정체성 | j9main·sens·G1·cases·D·probe-repro·12a·12b | **t8·L1 기준 줄 없음(B-3)** |
| 6.2 sens J-P3 | `_sens_jp3` 879-894 | **범위 불일치(B-1)** |
| 6.3 G1 k=3·FAULT 171·J-P3 171 | 1062-1111 | 맞음 |
| P7-3·P7-9 재현 불일치 → setting_defect | probe-repro 1331 | **실패로 분류(M-1)** |
| 정오 1-3 decide 형식·`--spec` | `jp3_12b_judge_ed7.py:91-164` | 맞음(형식 거부 시험 있음) |
| 정오 1-7 cases E·F 10줄 | `judge_cases` 1176-1206 | 맞음 |
| 정오 1-10 단계 기록·폴더 소속·selection sha | `step_output_problems` 197-218, 12b `step_problems` 250-274 | 맞음(R-11) |
| 정오 1-11 j9main 200 | `J9_MAIN_JUDGED_ROWS` 123, 723 | 맞음 |

## 확인 필요
- Q-1(B-2): 12a·12b의 J-P3에 ③ rev 7 조건 읽기를 넣을지(넣으면 T′), 아니면 판 6 꼴로 정하고 정오 1-13 문장을 고칠지. 결과 전에 정한다.
- Q-2(M-1): probe-repro에서 고정 표 64행 범위의 해시 불일치를 `setting_defect`로 할지(6.1·P7-9 문면), P7-3 114행 전체를 실패 관문으로 둘지.
- Q-3(B-1): sens J-P3를 판정 4설정으로 한정하는 것(키 파일 104와 같음)이 의도인지.

## 위임 필요
- python-expert(T′, C의 자식 커밋 하나, 허용 경로는 5.2 그대로)
  - `jp3_ed7_judge.py:879-894` sens J-P3를 judged 줄로 한정하고 기록 설정은 기록으로 돌린다. 460줄 꼴 합성 시험을 더한다.
  - (Q-1 답에 따라) 12a t12 새 쪽과 12b judge 판정 줄에 `condition_judgement`를 넣는다.
  - `judge_t8`에 `identity_defects`(VBM·VBM0)와 VBM0 실제 태그 기록을 넣는다.
  - L1 기준 4개의 6.1 정체성 대조와 출처별 기록을 넣는다.
  - (Q-2 답에 따라) probe-repro 분류를 고친다.
  - 끝나면 P7-11(범위·목록·시험 범위)과 이 감사를 다시 받는다.
- control-expert: 정오 1을 고친다.
  - B-3: T′을 만들지 않을 경우 1-8·1-9 문면
  - B-2: Q-1 결과에 따른 1-13 문면
  - M-2: 1-7 권고의 관문 여부와 실행 조건
  - M-3: 1-2 조건 1 명령
  - M-4: 판정서에 옮길 목록
  - R-3: 목록 sha 인용
  - R-7·R-8: 문면 정리
- tools/verif 후보(python-expert): "문자열 키 리터럴 대 계획 seed 충돌 미리 보기"(입력: noise json, `05_tests` 루트들, seed 범위. 출력: 충돌 건수. 종료 0/1/2). 이번에 즉석 스크립트로 했다.

## 메인 세션 권고(본 실행 전후 절차, 볼 것 4)
1. 정오 1을 고친 뒤 봉인한다(sha와 `.sha256`, LF, `-text`는 이미 걸려 있음). 그다음 근거 폴더 4개(`run_commit_8a2a52ce`, `suite_8a2a52ce`, `judge_commit_c91065b7`, `postseal` + SUMS)를 함께 커밋한다. 커밋 전에 `git status --ignored`를 본다. P7-2 범위를 좁히는 정오이므로 실행 시작 전에 봉인한다.
2. T′을 만들고 P7-11·재감사를 실행 전에 끝낸다(M-6). ed7-impl·ed7-judge(새 T′ worktree)는 판정이 끝날 때까지 lock하고, 그 안에서 커밋하지 않는다.
3. 메인 checkout에 `prelaunch_j9\ed7_run_config.json`을 템플릿에서 만들고 `run_commit` 전체 sha와 worktree 절대경로를 채운다. 이어서 `placeholder_scan.py <그 파일> --pattern-set both`(종료 0)와 `<ed7-impl>\…\run_steps_ed7\check_ed7.ps1`(종료 0)을 확인한다.
4. 배치: run_v5 단계(t8·cases·probe·confirm·j9main·sens)의 `-MaskHex`·`-Workers`는 compute-scheduler-expert 배치표로 받는다. r79 단계는 P 1/4 고정이다. `reserve.py` 예약을 잡고, 실행 시작 때 외부 도구(baseline_check·record·sample) sha를 기록한다(R-5).
5. 순서: scope → l1ref → t8 → cases → probe → confirm → j9main → sens → dg3 → 12b_plan → 12b_vbkm0 base. 12b_vbkm0 b4와 12b_vbkm은 T′ 감사 뒤 decide 결과를 받아서만 돌린다(1-1·1-3).
6. 각 단계의 `.done`이 생기면 곧바로 그 단계 폴더에 `tools\verif\baseline_check.py write-sums <폴더> --recursive`를 돌리고, SUMS sha를 기록한다(1-10).
7. 10a(12b_plan) 바로 전에 c92·c93의 sha256(fa538512… / e5d1d52e…)과 HEAD blob이 같은지 확인하고 기록한다. 명령은 `git diff --quiet HEAD -- <두 경로>`다(1-2 조건 1, M-3). 다르면 10a를 돌리지 않는다.
8. 각 T′ 판정 직전에 `baseline_check.py sums <단계 폴더>`로 불일치 0을 확인한다. 판정 명령에는 `--step-done <해당 .done>`을 주고, 12b decide에는 `--spec <메인 checkout 명세>`를 더한다. `--out`은 T′ worktree 밖이자 단계 폴더 밖에 둔다(M-5). decide 출력의 sha를 `-DecisionSha256`으로 넘긴다.
9. 정오 1-7의 P5-1형 33줄 기록 실행을 한다면(M-2 확정 뒤) 출력은 C worktree 밖이자 `j9_runs\8a2a52ce` 밖에 두고, 실행 단계와 겹치지 않게 돌린다.
10. 판정 전에는 이 감사의 실행 전 도구들을 실제 출력에 다시 돌린다.
    - `log_errors.py <각 단계 logs>`: 종료 0
    - `key_presence.py`: 판정이 읽는 키(`identity_end`, `selection_sha256` 등)
    - (B-2를 넣는다면) `key_presence.py --npz-dir <dg3·12b T4h> --array jp3_t_s,jp3_class,jp3_plant_state,jp3_p_tr_Pa,jp3_used_bound_Pa`

## 검사하지 못한 것
- T 판정 도구를 실제 데이터에 실행하지 않았다(본 실행 금지). 그래서 B-1은 코드와 키 파일로 추적한 결론이다.
- `ed7_condition3_adoption.py`의 T 변경(5.2-9, 46행)은 단위 시험 통과만 확인하고 규칙과 줄 단위로 대조하지 않았다.
- `jp3_12b_judge.py`·`jp3_tjr_judge.py`(이어받은 판 5·6 도구)의 내부 동작 중 판 7 래퍼가 바꾸지 않는 부분은 다시 감사하지 않았다.
- 06_analysis 전체를 대상으로 한 12b 스캔은 블라인드 때문에 미리 보지 않았다(05_tests 리터럴만 확인).
- 실행 경로 목록이 빠짐없는지 정확히는 확인하지 못했다. 넓게 잡은 닫힘으로 "T 변경이 실행 경로에 들지 않음"만 확인했다.
- `baseline_check identity`가 실제 run_v5·ed7_probe 출력에서 어떻게 동작하는지는 건식으로 시험할 수 없다. 판 6 출력에 `*.identity.json`이 있었던 선례만 확인했다.

## 실행한 검증
- 인터프리터: python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`). 프로젝트 env는 쓰지 않았고, 판정 도구를 import하지 않았다.
- git(조회 전용)
  - `diff --name-status b46bdf8f 8a2a52ce`, `diff … -- 03_src`, `diff 8a2a52ce c91065b7`(이름과 rules·condition 본문)
  - `rev-parse` 03_src tree, `ls-files --eol`, `check-attr text eol`, `check-ignore -v`, `status --porcelain`, `hash-object`, `show 3ecf61f1:…/d_grid_keys12.json`
- 해시: Get-FileHash로 고정 입력 14개를 쟀다(T의 PINNED_SHA256, common_ed7 값과 모두 같음). evidence SUMS 5개, handback 4개도 쟀다.
- 도구(`~/.claude/tools/verif`)
  - `log_errors.py`(C dry_run): 0, 근거 없음
  - `placeholder_scan.py run_steps_ed7 --pattern-set both --allow <ED7_RUN_COMMIT> --allow <ED7_RUN_WORKTREE>`: 0, 허용 2
  - `ps1_lint.py` 14파일: 0
  - `gate_scan.py` T 판정 파일 5개: warning 6, 모두 코드를 읽고 분류함
  - `junit_skips.py` C·T: C는 실패 2·건너뜀 15(기준선 안), T는 0
  - `ref_check.py --exclude`(블라인드 3, `.claude`, 판 6 selection.json), 정오 1: no-git / `--rev c91065b7`. C·T·3ecf61f1 트리 이름과 사용자 도구 경로로 설명된다
  - `ref_check.py --rev e241638d`, 명세: 같은 분류
  - `seal_check.py --quoted erratum --min-hex-len 13 --hash-files …`: raw 일치, 미해결 1은 D blob sha로 확인한 오탐
  - `baseline_check.py sums` 5개 폴더: 불일치·누락·목록 밖 0, `cited_untracked`는 미커밋
- 즉석 스크립트(scratchpad `verif-ed7prerun\`, 모두 지움)
  - `seedscan.py`: 05_tests 리터럴 대 12b seed
  - `closure.py`: 독립 import 닫힘과 목록 blob을 C·T에서 대조
  - `mtime.py`: C 변경 파일 mtime
  - `showgate.py`·`showref.py`: 도구 json 요약
- 부산물: T worktree `04_scripts\**\__pycache__`(ignored)는 17:25에 생긴 것으로 T 시험 실행 때 남았고 내가 만들지 않았다. scratchpad 하위 폴더는 삭제를 확인했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v7.md 10902ffd…, jp3_remedy_spec_v7.md.sha256 8cfd1981…, jp3_remedy_spec_v7_erratum1.md cd05e1ea…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

메모리 반영안(메인 판단): "2축 판정(판정 설정 + 기록 설정) 묶음에서는 행 수 기대값을 키 파일이 판정 줄만으로 세는데 도구는 전체 줄로 집계해 결정적 setting_defect가 나는 꼴이 있다. e2e 시험이 판정 설정 줄만 써서 이를 덮는다. 판정 하위 명령마다 '집계 집합'과 '기대값 출처'의 범위를 대조할 것." 이번 실행에서는 메모리 파일에 쓰지 않았다.
